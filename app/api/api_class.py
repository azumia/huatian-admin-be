import logging
import random
from types import CodeType, new_class
import uuid
import os
from flask import Blueprint, jsonify, session, request, current_app
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy.sql.expression import null
from app.models.model import Class, StuCls, Student, Teacher, Log, User, ClsWd
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

bp = Blueprint("class", __name__, url_prefix='/class/')

logger = logging.getLogger(__name__)

@route(bp, '/list', methods=["GET"])
@login_required
def class_list():
    """
    获取班级列表
    :return:
    """
    res = ResMsg()
    obj = request.args
    class_name = obj.get("name") or ''
    # student = obj.get("student") or ''
    teacher_id = obj.get("teacher_id") or None
    weekday = obj.get("weekday") or None
    status = obj.get("status") or None
    page_index = int(obj.get("page"))
    page_size = int(obj.get("count"))
    # 找出符合星期的所有数据
    n_cls_wd = db.session.query(ClsWd).filter(or_(ClsWd.weekday == weekday, weekday == None)).all()
    all_cls_wd = db.session.query(ClsWd).all()
    db_class_id = db.session.query(Class).all()
    fit_ids = []
    if weekday == None:
        for cls in db_class_id:
            fit_ids.append(cls.id)
    else:
        if len(n_cls_wd) > 0:
            for cw in n_cls_wd:
                fit_ids.append(cw.class_id)
    
    filters = {
        or_(Class.class_name.like('%' + class_name + '%'), class_name == None),
        or_(Class.teacher_id == teacher_id, teacher_id == None),
        or_(Class.id.in_(fit_ids), fit_ids == []),
        or_(Class.status == status, status == None)
    }

    db_class = db.session.query(Class, Teacher).\
        outerjoin(Teacher, Class.teacher_id == Teacher.id).\
        filter(*filters).order_by(Class.id).\
        limit(page_size).offset((page_index-1)*page_size).all()
    total_count = db.session.query(Class, Teacher).\
        outerjoin(Teacher, Class.teacher_id == Teacher.id).\
        filter(*filters).count()
    all_student = db.session.query(Student).all()
    # filter_student = db.session.query(Student).filter(or_(Student.name.like('%' + student + '%'), student == None)).all()
    # current_app.logger.debug(db.session.query(Class, Teacher).\
    #     outerjoin(Teacher, Class.teacher_id == Teacher.id).\
    #     filter(*filters))
    # total_count = len(db_class)
    class_list = []
    for o in db_class:
        # 处理班级下面的学员信息
        student_id_arr = []
        n_stu_cls = db.session.query(StuCls).filter(StuCls.class_id == o[0].id).all()
        for stu in n_stu_cls:
            student_id_arr.append(str(stu.student_id))
        
        student_list = []
        if len(student_id_arr) > 0:
            for sid in student_id_arr:
                for stu in all_student:
                    if str(sid) == str(stu.id):
                        student_list.append(stu)
        # 处理班级的星期信息
        weekdayArr = []
        for cw in all_cls_wd:
            if cw.class_id == o[0].id:
                weekdayArr.append(cw.weekday)
        
        class_list.append({
            "id": o[0].id,
            "class_name": o[0].class_name,
            "min_num": o[0].min_num,
            "max_num": o[0].max_num,
            "now_num": len(student_list),
            "teacher_name": o[1].name if o [1] != None else None,
            "teacher_id": o[1].id if o [1] != None else None,
            "total_hour": o[0].total_hour,
            "weekday": weekdayArr,
            "begin_time": o[0].begin_time,
            "end_time": o[0].end_time,
            "classroom": o[0].classroom,
            "status": o[0].status,
            "target": o[0].target,
            "student_id": student_list
        })
    data = {
            "classes": class_list,
            "page": page_index,
            "count": page_size,
            "total": total_count
            }
    res.update(data=data)
    return res.data

@route(bp, '/add', methods=["POST"])
@login_required
def class_add():
    """
    新增班级信息
    :return:
    """
    res = ResMsg()
    obj = request.json
    n_class = Class()
    n_class.class_name = obj["name"]
    n_class.target = obj["target"]
    # n_class.weekday = obj["weekday"] or None
    n_class.begin_time = obj["begin_time"]
    n_class.end_time = obj["end_time"]
    n_class.min_num = obj["min_num"] or None
    n_class.max_num = obj["max_num"] or None
    n_class.classroom = obj["classroom"]
    n_class.total_hour = obj["total_hour"] or None
    n_class.teacher_id = obj["teacher_id"] or None
    n_class.status = obj["status"]
    n_class.create_time = datetime.now()
    n_class.update_time = datetime.now()
    try:
        db.session.add(n_class)
        db.session.flush()
        # 处理班级，星期对应数据
        if len(obj['weekday']) > 0:
            for day in obj['weekday']:
                n_cls_wd = ClsWd()
                n_cls_wd.class_id = n_class.id
                n_cls_wd.weekday = day
                db.session.add(n_cls_wd)
                db.session.commit()
        # 处理班级，学员对应数据
        if len(obj["studentArr"]) > 0:
            for o in obj["studentArr"]:
                add_stu_cls(o["id"], n_class.id)
        db.session.commit()
    except:
        db.session.rollback()
    return res.data

@route(bp, '/edit', methods=["POST"])
@login_required
def class_edit():
    """
    编辑班级信息
    :return:
    """
    res = ResMsg()
    obj = request.json
    n_class = db.session.query(Class).filter(Class.id == obj["id"]).first()
    n_class.class_name = obj["name"]
    n_class.target = obj["target"]
    # n_class.weekday = obj["weekday"] or None
    n_class.begin_time = obj["begin_time"]
    n_class.end_time = obj["end_time"]
    n_class.min_num = obj["min_num"] or None
    n_class.max_num = obj["max_num"] or None
    n_class.classroom = obj["classroom"]
    n_class.total_hour = obj["total_hour"] or None
    n_class.teacher_id = obj["teacher_id"] or None
    n_class.status = obj["status"]
    n_class.update_time = datetime.now()

    studentIdArr = []
    if len(obj["studentArr"]) > 0:
        for o in obj["studentArr"]:
            studentIdArr.append(str(o["id"]))
    stuClsIdArr = []
    n_stu_cls = db.session.query(StuCls).filter(StuCls.class_id == n_class.id).all()
    for stu in n_stu_cls:
        stuClsIdArr.append(str(stu.student_id))
    user = db.session.query(User).filter(User.name == session["user_name"]).first()
    try:
        db.session.add(n_class)
        db.session.commit()
        # 处理班级，星期对应数据
        if len(obj['weekday']) > 0:
            db.session.query(ClsWd).filter(ClsWd.class_id == n_class.id).delete(synchronize_session=False)
            db.session.commit()
            for day in obj['weekday']:
                n_cls_wd = ClsWd()
                n_cls_wd.class_id = n_class.id
                n_cls_wd.weekday = day
                db.session.add(n_cls_wd)
                db.session.commit()
        # 处理班级，学员对应数据
        if len(studentIdArr) > 0:
            for sid in studentIdArr:
                if sid not in stuClsIdArr:
                    add_stu_cls(sid, n_class.id)
                    # 添加日志
                    add_log(2, user.id, sid, n_class.teacher_id, n_class.id, '将其添加到了班级：' + n_class.class_name + '中')
            for ssid in stuClsIdArr:
                if ssid not in studentIdArr:
                    delete_stu_cls(ssid, n_class.id)
                    # 添加日志
                    add_log(2, user.id, ssid, n_class.teacher_id, n_class.id, '将其从班级：' + n_class.class_name + '中移除')
    except:
        db.session.rollback()
    return res.data

@route(bp, '/delete', methods=["POST"])
@login_required
def class_delete():
    """
    删除班级信息
    :return:
    """
    res = ResMsg()
    obj = request.json
    n_class = db.session.query(Class).filter(Class.id == obj["id"]).first()
    n_stu_cls = db.session.query(StuCls).filter(StuCls.class_id == obj["id"]).all()
    try:
        db.session.delete(n_class)
        db.session.delete(n_stu_cls)
        db.session.commit()
    except:
        db.session.rollback()
    return res.data

@route(bp, '/verify', methods=["POST"])
@login_required
def class_verify():
    """
    销课
    :return:
    """
    res = ResMsg()
    obj = request.json
    student_ids = obj['studentIds']
    hour = int(obj['hour'])
    remark = obj['remark']
    class_id = obj['classId']
    teacher_id = obj['teacherId']
    n_class = db.session.query(Class).filter(Class.id == class_id).first()
    for id in student_ids:
        student = db.session.query(Student).filter(Student.id == id).first()
        if student.left_hour < hour:
            res.update(code=ResponseCode.Fail, msg='某学生剩余课时已不足以销课，请检查后再操作')
            break
    for id in student_ids:
        student = db.session.query(Student).filter(Student.id == id).first()
        student.used_hour += hour
        student.left_hour -= hour
        student.update_time = datetime.now()
        
        user = db.session.query(User).filter(User.name == session["user_name"]).first()
        try:
            add_log(3, user.id, id, teacher_id, class_id, '在班级：' + n_class.class_name + ' 消耗课时：' + str(hour) + '课时，销课备注为：' + remark)
            db.session.add(student)
            db.session.commit()
        except:
            db.session.rollback()
    return res.data
