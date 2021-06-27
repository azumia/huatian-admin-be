import logging
import random
import uuid
import os
from flask import Blueprint, jsonify, session, request, current_app
from datetime import datetime, timedelta
from decimal import Decimal
from app.models.model import Class, Log, StuCls, Student, Teacher, User
from app.utils.core import db

from sqlalchemy import or_, and_

from app.api.tree import Tree
from app.utils.code import ResponseCode
from app.utils.response import ResMsg
from app.utils.util import route, Redis, CaptchaTool, PhoneTool
from app.utils.auth import Auth, login_required
from app.api.report import excel_write, word_write, pdf_write
from app.api.wx_login_or_register import get_access_code, get_wx_user_info, wx_login_or_register
from app.api.phone_login_or_register import SendSms, phone_login_or_register
from app.celery import add, flask_app_context

bp = Blueprint("log", __name__, url_prefix='/log/')

logger = logging.getLogger(__name__)

@login_required
def add_log(type, operator_id, student_id, teacher_id, class_id, remark):
    """
    新增日志
    :return:
    """
    res = ResMsg()
    n_log = Log()
    n_log.type = type
    n_log.operator_id = operator_id
    n_log.student_id = student_id
    n_log.teacher_id = teacher_id
    n_log.class_id = class_id
    n_log.remark = remark
    n_log.time = datetime.now()
    db.session.add(n_log)
    db.session.commit()
    return res.data


@route(bp, '/list', methods=["GET"])
@login_required
def log_list():
    """
    获取日志列表
    :return:
    """
    current_app.logger.debug('aodifoads')
    res = ResMsg()
    obj = request.args
    n_user = db.session.query(User).all()
    n_teacher = db.session.query(Teacher).all()
    n_student = db.session.query(Student).all()
    n_class = db.session.query(Class).all()
    n_log = db.session.query(Log).filter(Log.student_id == obj['sid']).all()
    dataList = []
    for log in n_log:
        logObj = log
        for user in n_user:
            if user.id == log.operator_id:
                logObj.operator_name = user.nick_name
        for teacher in n_teacher:
            if teacher.id == log.teacher_id:
                logObj.teacher_name = teacher.name
        for student in n_student:
            if student.id == log.student_id:
                logObj.student_name = student.name
        for cls in n_class:
            if cls.id == log.class_id:
                logObj.class_name = cls.class_name
        dataList.append(logObj)
    data = {
        dataList: dataList
    }
    res.update(data=data)
    return res.data

