import logging
import random
import uuid
import os
from flask import Blueprint, jsonify, session, request, current_app
from datetime import datetime, timedelta
from decimal import Decimal
from app.models.model import Teacher
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

bp = Blueprint("teacher", __name__, url_prefix='/teacher/')

logger = logging.getLogger(__name__)

@route(bp, '/list', methods=["GET"])
# @bp.route('/list', methods=["GET"])
@login_required
def teacher_list():
    """
    获取教师列表
    :return:
    """
    res = ResMsg()
    obj = request.args
    name = obj.get("name") or None
    filters = {
        or_(Teacher.name == name, name == None)
    }
    # current_app.logger.debug(db.session.query(Teacher.id.label('iduu'), Teacher.name).filter(*filters).order_by(Teacher.id))
    # db_teacher = db.session.query(Teacher.id.label('iduu'), Teacher.name).filter(*filters).order_by(Teacher.id).all()
    # for o in db_teacher:
    #     current_app.logger.debug(o[0])
    db_teacher = db.session.query(Teacher).filter(*filters).order_by(Teacher.id).all()
    teacher_list = []
    for o in db_teacher:
        teacher_list.append({
            "id": o.id,
            "name": o.name
        })
    data = {
            "teachers": teacher_list
            }
    # current_app.logger.debug(type(db_teacher))
    res.update(data=data)
    return res.data

