import logging
import random
import uuid
import os
from flask import Blueprint, jsonify, session, request, current_app
from datetime import datetime, timedelta
from decimal import Decimal
from app.models.model import StuCls
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

bp = Blueprint("stucls", __name__, url_prefix='/stucls/')

logger = logging.getLogger(__name__)

@login_required
def add_stu_cls(sid, cid):
    """
    新增学生-班级对应数据
    :return:
    """
    res = ResMsg()
    n_stu_cls = StuCls()
    n_stu_cls.student_id = sid
    n_stu_cls.class_id = cid
    db.session.add(n_stu_cls)
    db.session.commit()
    return res.data

@login_required
def delete_stu_cls(sid, cid):
    """
    删除学生-班级对应数据
    :return:
    """
    res = ResMsg()
    n_stu_cls = db.session.query(StuCls).filter(StuCls.student_id == sid , StuCls.class_id == cid).first()
    db.session.delete(n_stu_cls)
    db.session.commit()
    return res.data

