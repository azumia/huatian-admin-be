import logging
import random
import uuid
import os
import copy
from flask import Blueprint, jsonify, session, request, current_app
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy.sql.elements import Null
from app.models.model import Class, Student, StuCls, User, Log, Teacher, ClsWd
from app.utils.core import db

from sqlalchemy import or_, and_

from app.api.tree import Tree
from app.api.api_stu_cls import add_stu_cls, delete_stu_cls
from app.api.api_log import add_log
from app.utils.code import ResponseCode
from app.utils.response import ResMsg
from app.utils.util import route, Redis, CaptchaTool, PhoneTool
from app.utils.auth import Auth, login_required
from app.api.report import excel_write, word_write, pdf_write
from app.api.wx_login_or_register import get_access_code, get_wx_user_info, wx_login_or_register
from app.api.phone_login_or_register import SendSms, phone_login_or_register
from app.celery import add, flask_app_context

bp = Blueprint("student", __name__, url_prefix='/student/')

logger = logging.getLogger(__name__)

@route(bp, '/list', methods=["GET"])
@login_required
def student_list():
    """
    获取学员列表
    :return:
    """
    res = ResMsg()
    # obj = request.get_json(force=True)
    obj = request.args
    name = obj.get("name") or None
    phone = obj.get("phone") or None
    type = obj.get("type") or None
    page_index = int(obj.get("page"))
    page_size = int(obj.get("count"))
    filters = {
        or_(Student.name == name, name == None),
        or_(Student.phone == phone, phone == None),
        or_(Student.type == type, type == None),
    }
    # current_app.logger.debug(db.session.query(Student).filter(*filters).order_by(Student.id).limit(page_size).offset((page_index-1)*page_size))
    db_student = db.session.query(Student).filter(*filters).order_by(Student.id).limit(page_size).offset((page_index-1)*page_size).all()
    total_count = db.session.query(Student).filter(*filters).count()
    all_class = db.session.query(Class).all()
    student_list = []
    for stu in db_student:
        class_id = []
        n_stu_cls = db.session.query(StuCls).filter(StuCls.student_id == stu.id).all()
        for nstu in n_stu_cls:
            for cla in all_class:
                if nstu.class_id == cla.id:
                    class_id.append(cla)
        student_list.append({
            'id': stu.id,
            'name': stu.name,
            'type': stu.type,
            'phone': stu.phone,
            'birthday': stu.birthday,
            'age': stu.age,
            'class_id': class_id,
            'used_hour': stu.used_hour,
            'left_hour': stu.left_hour,
            'remark': stu.remark
        })
    data = {
            "students": student_list,
            "page": page_index,
            "count": page_size,
            "total": total_count
            }
    
    res.update(data=data)
    return res.data

@route(bp, '/detail', methods=["GET"])
@login_required
def student_detail():
    """
    获取单个学员信息
    :return:
    """
    res = ResMsg()
    obj = request.args
    db_student = db.session.query(Student).filter(Student.id == obj['id']).first()
    n_stu_cls = db.session.query(StuCls).filter(StuCls.student_id == obj['id']).all()
    stu_cls_ids = []
    for stucls in n_stu_cls:
        stu_cls_ids.append(stucls.class_id)
    n_class = db.session.query(Class).filter(Class.id.in_(stu_cls_ids)).all()
    data = {
            "detail": db_student,
            "classes": n_class
            }
    
    res.update(data=data)
    return res.data


@route(bp, '/add', methods=["POST"])
@login_required
def student_add():
    """
    新增学员信息
    :return:
    """
    res = ResMsg()
    obj = request.json
    n_student = Student()
    n_student.name = obj["name"]
    n_student.phone = obj["phone"]
    n_student.birthday = obj["birthday"] or None
    n_student.age = obj["age"] or None
    n_student.used_hour = obj["used_hour"] or None
    n_student.left_hour = obj["left_hour"] or None
    n_student.type = obj["type"] or None
    n_student.remark = obj["remark"] or None
    n_student.status = obj["status"] or None
    n_student.create_time = datetime.now()
    n_student.update_time = datetime.now()
    user = db.session.query(User).filter(User.name == session["user_name"]).first()
    try:
        db.session.add(n_student)
        db.session.flush()
        # 添加日志
        add_log(1, user.id, n_student.id, None, None, '新增了学员信息')
        if len(obj["classArr"]) > 0:
            for o in obj["classArr"]:
                add_stu_cls(n_student.id, o["id"])
        db.session.commit()
    except:
        db.session.rollback()
    return res.data

@route(bp, '/edit', methods=["POST"])
@login_required
def student_edit():
    """
    编辑学员信息
    :return:
    """
    res = ResMsg()
    obj = request.json
    # o_student = db.session.query(Student).filter(Student.id == obj["id"]).first()
    n_student = db.session.query(Student).filter(Student.id == obj["id"]).first()
    o_student = copy.deepcopy(n_student)
    n_student.name = obj["name"]
    n_student.phone = obj["phone"]
    n_student.birthday = obj["birthday"] or None
    n_student.age = obj["age"] or None
    n_student.used_hour = obj["used_hour"] or None
    n_student.left_hour = obj["left_hour"] or None
    n_student.type = obj["type"] or None
    n_student.remark = obj["remark"]
    n_student.status = obj["status"] or None
    n_student.update_time = datetime.now()

    classIdArr = []
    if len(obj["classArr"]) > 0:
        for o in obj["classArr"]:
            classIdArr.append(str(o["id"]))
    stuClsIdArr = []
    n_stu_cls = db.session.query(StuCls).filter(StuCls.student_id == n_student.id).all()
    user = db.session.query(User).filter(User.name == session["user_name"]).first()
    n_class = db.session.query(Class).all()
    for stu in n_stu_cls:
        stuClsIdArr.append(str(stu.class_id))
    try:
        # 如果更改了课时，则添加日志
        if o_student.used_hour != n_student.used_hour or o_student.left_hour != n_student.left_hour:
            add_log(3, user.id, n_student.id, None, None, '更改了课时，更改前已用课时 ' + str(o_student.used_hour) + ',剩余课时 ' + str(o_student.left_hour) + '; 更改后已用课时 ' + str(n_student.used_hour) + ',剩余课时 ' + str(n_student.left_hour))
        elif o_student.remark != n_student.remark:
            add_log(1, user.id, n_student.id, None, None, '将备注更改为: ' + n_student.remark)
        else:
            add_log(1, user.id, n_student.id, None, None, '更改了学员资料')
        db.session.add(n_student)
        db.session.commit()
        if len(classIdArr) > 0:
            for cid in classIdArr:
                if cid not in stuClsIdArr:
                    add_stu_cls(n_student.id, cid)
                    # 添加日志
                    class_name = ''
                    for nls in n_class:
                        if nls.id == cid:
                            class_name = nls.class_name
                            break
                    add_log(2, user.id, n_student.id, None, None, '将其添加到了班级：' + class_name + '中')
            for ccid in stuClsIdArr:
                if ccid not in classIdArr:
                    delete_stu_cls(n_student.id, ccid)
                    # 添加日志
                    class_name = ''
                    for nls in n_class:
                        if nls.id == ccid:
                            class_name = nls.class_name
                            break
                    add_log(2, user.id, n_student.id, None, None, '将其添加从班级：' + class_name + '中移除')
    except:
        db.session.rollback()
    return res.data

@route(bp, '/delete', methods=["POST"])
@login_required
def student_delete():
    """
    删除学员信息
    :return:
    """
    res = ResMsg()
    obj = request.json
    n_student = db.session.query(Student).filter(Student.id == obj["id"]).first()
    n_stu_cls = db.session.query(StuCls).filter(StuCls.student_id == obj["id"])
    try:
        db.session.delete(n_student)
        n_stu_cls.delete(synchronize_session=False)
        db.session.commit()
    except:
        db.session.rollback()
    return res.data

@route(bp, '/logs', methods=["GET"])
@login_required
def log_list():
    """
    获取日志列表
    :return:
    """
    res = ResMsg()
    obj = request.args
    n_user = db.session.query(User).all()
    n_teacher = db.session.query(Teacher).all()
    n_student = db.session.query(Student).all()
    n_class = db.session.query(Class).all()
    n_log = db.session.query(Log).filter(Log.student_id == obj['sid']).order_by(Log.id.desc()).all()
    dataList = []
    if len(n_log) > 0:
        for log in n_log:
            operator_name = ''
            teacher_name = ''
            student_name = ''
            class_name = ''
            for user in n_user:
                if user.id == log.operator_id:
                    operator_name = user.nick_name
            for teacher in n_teacher:
                if teacher.id == log.teacher_id:
                    teacher_name = teacher.name
            for student in n_student:
                if student.id == log.student_id:
                    student_name = student.name
            for cls in n_class:
                if cls.id == log.class_id:
                    class_name = cls.class_name
            dataList.append({
                'id': log.id,
                'type': log.type,
                'time': log.time,
                'teacher_id': log.teacher_id,
                'teacher_name': teacher_name,
                'student_id': log.student_id,
                'student_name': student_name,
                'class_id': log.class_id,
                'class_name': class_name,
                'operator_id': log.operator_id,
                'operator_name': operator_name,
                'remark': log.remark
            })
    data = {
        'dataList': dataList
    }
    res.update(data=data)
    return res.data

@route(bp, '/course', methods=["GET"])
@login_required
def course_list():
    """
    获取课程列表
    :return:
    """
    res = ResMsg()
    obj = request.args
    stu_cls = db.session.query(StuCls).filter(StuCls.student_id == obj['sid']).all()
    classid_arr = []
    for sc in stu_cls:
        classid_arr.append(sc.class_id)
    cls_wd = db.session.query(ClsWd).filter(ClsWd.class_id.in_(classid_arr)).all()
    n_class = db.session.query(Class).filter(Class.id.in_(classid_arr)).all()
    weekSet = set([])
    for sw in cls_wd:
        weekSet.add(sw.weekday)
    course_list = {}
    for wd in weekSet:
        week_cls = []
        # 获取每周几的班级id列表
        for clswd in cls_wd:
            if clswd.weekday == wd:
                week_cls.append(clswd.class_id)
        cls_arr = []
        for wc in week_cls:
            for nc in n_class:
                if wc == nc.id:
                    cls_arr.append(nc)
        course_list[wd] = cls_arr
    res.update(data = {
        'course_list': course_list
    })
    return res.data
    

# -----------------原生蓝图路由---------------#


@bp.route('/logs', methods=["GET"])
def test_logger():
    """
    测试自定义logger
    :return:
    """
    logger.info("this is info")
    logger.debug("this is debug")
    logger.warning("this is warning")
    logger.error("this is error")
    logger.critical("this is critical")
    data = User.query.all()
    return data
    # return "ok"


@bp.route("/unifiedResponse", methods=["GET"])
def test_unified_response():
    """
    测试统一返回消息
    :return:
    """
    res = ResMsg()
    test_dict = dict(name="zhang", age=18)
    res.update(code=ResponseCode.Success, data=test_dict)
    return jsonify(res.data)


# --------------使用自定义封装蓝图路由--------------------#


@route(bp, '/packedResponse', methods=["GET"])
def test_packed_response():
    """
    测试响应封装
    :return:
    """
    res = ResMsg()
    test_dict = dict(name="zhang", age=18)
    data = db.session.query(User).all()
    # data = User.name.query.all()
    logger.info(type(data))
    # 此处只需要填入响应状态码,即可获取到对应的响应消息
    res.update(code=ResponseCode.Success, data=data)
    # 此处不再需要用jsonify，如果需要定制返回头或者http响应如下所示
    # return res.data,200,{"token":"111"}
    return res.data


@route(bp, '/typeResponse', methods=["GET"])
def test_type_response():
    """
    测试返回不同的类型
    :return:
    """
    res = ResMsg()
    now = datetime.now()
    date = datetime.now().date()
    num = Decimal(11.11)
    test_dict = dict(now=now, date=date, num=num)
    # 此处只需要填入响应状态码,即可获取到对应的响应消息
    res.update(code=ResponseCode.Success, data=test_dict)
    # 此处不再需要用jsonify，如果需要定制返回头或者http响应如下所示
    # return res.data,200,{"token":"111"}
    return res.data


# --------------Redis测试封装--------------------#

@route(bp, '/testRedisWrite', methods=['GET'])
def test_redis_write():
    """
    测试redis写入
    """
    # 写入
    Redis.write("test_key", "test_value", 60)
    return "ok"


@route(bp, '/testRedisRead', methods=['GET'])
def test_redis_read():
    """
    测试redis获取
    """
    data = Redis.read("test_key")
    return data


# -----------------图形验证码测试---------------------------#

@route(bp, '/testGetCaptcha', methods=["GET"])
def test_get_captcha():
    """
    获取图形验证码
    :return:
    """
    res = ResMsg()
    new_captcha = CaptchaTool()
    img, code = new_captcha.get_verify_code()
    res.update(data=img)
    session["code"] = code
    return res.data


@route(bp, '/testVerifyCaptcha', methods=["POST"])
def test_verify_captcha():
    """
    验证图形验证码
    :return:
    """
    res = ResMsg()
    obj = request.get_json(force=True)
    code = obj.get('code', None)
    s_code = session.get("code", None)
    print(code, s_code)
    if not all([code, s_code]):
        res.update(code=ResponseCode.InvalidParameter)
        return res.data
    if code != s_code:
        res.update(code=ResponseCode.VerificationCodeError)
        return res.data
    return res.data


# --------------------JWT测试-----------------------------------------#

@route(bp, '/testLogin', methods=["POST"])
def test_login():
    """
    登陆成功获取到数据获取token和刷新token
    :return:
    """
    res = ResMsg()
    obj = request.get_json(force=True)
    user_name = obj.get("name")
    # 未获取到参数或参数不存在
    if not obj or not user_name:
        res.update(code=ResponseCode.InvalidParameter)
        return res.data

    if user_name == "qin":
        # 生成数据获取token和刷新token
        access_token, refresh_token = Auth.encode_auth_token(user_id=user_name)

        data = {"access_token": access_token.decode("utf-8"),
                "refresh_token": refresh_token.decode("utf-8")
                }
        res.update(data=data)
        return res.data
    else:
        res.update(code=ResponseCode.AccountOrPassWordErr)
        return res.data


@route(bp, '/testGetData', methods=["GET"])
@login_required
def test_get_data():
    """
    测试登陆保护下获取数据
    :return:
    """
    res = ResMsg()
    name = session.get("user_name")
    data = "{}，你好！！".format(name)
    res.update(data=data)
    return res.data


@route(bp, '/testRefreshToken', methods=["GET"])
def test_refresh_token():
    """
    刷新token，获取新的数据获取token
    :return:
    """
    res = ResMsg()
    refresh_token = request.args.get("refresh_token")
    if not refresh_token:
        res.update(code=ResponseCode.InvalidParameter)
        return res.data
    payload = Auth.decode_auth_token(refresh_token)
    # token被串改或过期
    if not payload:
        res.update(code=ResponseCode.PleaseSignIn)
        return res.data

    # 判断token正确性
    if "user_id" not in payload:
        res.update(code=ResponseCode.PleaseSignIn)
        return res.data
    # 获取新的token
    access_token = Auth.generate_access_token(user_id=payload["user_id"])
    data = {"access_token": access_token.decode("utf-8"), "refresh_token": refresh_token}
    res.update(data=data)
    return res.data


# --------------------测试Excel报表输出-------------------------------#

@route(bp, '/testExcel', methods=["GET"])
def test_excel():
    """
    测试excel报表输出
    :return:
    """
    res = ResMsg()
    report_path = current_app.config.get("REPORT_PATH", "./report")
    file_name = "{}.xlsx".format(uuid.uuid4().hex)
    path = os.path.join(report_path, file_name)
    path = excel_write(path)
    path = path.lstrip(".")
    res.update(data=path)
    return res.data


# --------------------测试Word报表输出-------------------------------#

@route(bp, '/testWord', methods=["GET"])
def test_word():
    """
    测试word报表输出
    :return:
    """
    res = ResMsg()
    report_path = current_app.config.get("REPORT_PATH", "./report")
    file_name = "{}.docx".format(uuid.uuid4().hex)
    path = os.path.join(report_path, file_name)
    path = word_write(path)
    path = path.lstrip(".")
    res.update(data=path)
    return res.data


# --------------------测试无限层级目录树-------------------------------#

@route(bp, '/testTree', methods=["GET"])
def test_tree():
    """
    测试无限层级目录树
    :return:
    """
    res = ResMsg()
    data = [
        {"id": 1, "father_id": None, "name": "01"},
        {"id": 2, "father_id": 1, "name": "0101"},
        {"id": 3, "father_id": 1, "name": "0102"},
        {"id": 4, "father_id": 1, "name": "0103"},
        {"id": 5, "father_id": 2, "name": "010101"},
        {"id": 6, "father_id": 2, "name": "010102"},
        {"id": 7, "father_id": 2, "name": "010103"},
        {"id": 8, "father_id": 3, "name": "010201"},
        {"id": 9, "father_id": 4, "name": "010301"},
        {"id": 10, "father_id": 9, "name": "01030101"},
        {"id": 11, "father_id": 9, "name": "01030102"},
    ]

    new_tree = Tree(data=data)

    data = new_tree.build_tree()

    res.update(data=data)
    return res.data


# --------------------测试微信登陆注册-------------------------------#

@route(bp, '/testWXLoginOrRegister', methods=["GET"])
def test_wx_login_or_register():
    """
    测试微信登陆注册
    :return:
    """
    res = ResMsg()
    code = request.args.get("code")
    flag = request.args.get("flag")
    # 参数错误
    if code is None or flag is None:
        res.update(code=ResponseCode.InvalidParameter)
        return res.data
    # 获取微信用户授权码
    access_code = get_access_code(code=code, flag=flag)
    if access_code is None:
        res.update(code=ResponseCode.WeChatAuthorizationFailure)
        return res.data
    # 获取微信用户信息
    wx_user_info = get_wx_user_info(access_data=access_code)
    if wx_user_info is None:
        res.update(code=ResponseCode.WeChatAuthorizationFailure)
        return res.data

    # 验证微信用户信息本平台是否有，
    data = wx_login_or_register(wx_user_info=wx_user_info)
    if data is None:
        res.update(code=ResponseCode.Fail)
        return res.data
    res.update(data=data)
    return res.data


# --------------------测试手机短信验证码登陆注册-------------------------------#

@route(bp, '/testGetVerificationCode', methods=["GET"])
def test_get_verification_code():
    """
    获取手机验证码
    :return:
    """
    now = datetime.now()
    res = ResMsg()

    category = request.args.get("category", None)
    # category 参数如下：
    # authentication: 身份验证
    # login_confirmation: 登陆验证
    # login_exception: 登陆异常
    # user_registration: 用户注册
    # change_password: 修改密码
    # information_change: 信息修改

    phone = request.args.get('phone', None)

    # 验证手机号码正确性
    re_phone = PhoneTool.check_phone(phone)
    if phone is None or re_phone is None:
        res.update(code=ResponseCode.MobileNumberError)
        return res.data
    if category is None:
        res.update(code=ResponseCode.InvalidParameter)
        return res.data

    try:
        # 获取手机验证码设置时间
        flag = Redis.hget(re_phone, 'expire_time')
        if flag is not None:
            flag = datetime.strptime(flag, '%Y-%m-%d %H:%M:%S')
            # 判断是否重复操作
            if (flag - now).total_seconds() < 60:
                res.update(code=ResponseCode.FrequentOperation)
                return res.data

        # 获取随机验证码
        code = "".join([str(random.randint(0, 9)) for _ in range(6)])
        template_param = {"code": code}
        # 发送验证码
        sms = SendSms(phone=re_phone, category=category, template_param=template_param)
        sms.send_sms()
        # 将验证码存入redis，方便接下来的验证
        Redis.hset(re_phone, "code", code)
        # 设置重复操作屏障
        Redis.hset(re_phone, "expire_time", (now + timedelta(minutes=1)).strftime('%Y-%m-%d %H:%M:%S'))
        # 设置验证码过去时间
        Redis.expire(re_phone, 60 * 3)
        return res.data
    except Exception as e:
        logger.exception(e)
        res.update(code=ResponseCode.Fail)
        return res.data


@route(bp, '/testPhoneLoginOrRegister', methods=["POST"])
def test_phone_login_or_register():
    """
    用户验证码登录或注册
    :return:
    """
    res = ResMsg()

    obj = request.get_json(force=True)
    phone = obj.get('account', None)
    code = obj.get('code', None)
    if phone is None or code is None:
        res.update(code=ResponseCode.InvalidParameter)
        return res.data
    # 验证手机号和验证码是否正确
    flag = PhoneTool.check_phone_code(phone, code)
    if not flag:
        res.update(code=ResponseCode.InvalidOrExpired)
        return res.data

    # 登陆或注册
    data = phone_login_or_register(phone)

    if data is None:
        res.update(code=ResponseCode.Fail)
        return res.data
    res.update(data=data)
    return res.data


# --------------------测试PDF报表输出-------------------------------#

@route(bp, '/testPDF', methods=["GET"])
def test_pdf():
    """
    测试pdf报表输出
    :return:
    """
    res = ResMsg()
    report_path = current_app.config.get("REPORT_PATH", "./report")
    file_name = "{}.pdf".format(uuid.uuid4().hex)
    path = os.path.join(report_path, file_name)
    path = pdf_write(path)
    path = path.lstrip(".")
    res.update(data=path)
    return res.data


# --------------------测试Celery-------------------------------#


@route(bp, '/testCeleryAdd', methods=["GET"])
def test_add():
    """
    测试相加
    :return:
    """
    result = add.delay(1, 2)
    return result.get(timeout=1)


@route(bp, '/testCeleryFlaskAppContext', methods=["GET"])
def test_flask_app_context():
    """
    测试获取flask上下文
    :return:
    """
    result = flask_app_context.delay()
    return result.get(timeout=1)
