from datetime import datetime
from app.utils.core import db


class User(db.Model):
    """
    用户表
    """
    __tablename__ = 'ht_user'
    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    name = db.Column(db.String(255), nullable=False)  # 用户姓名
    nick_name = db.Column(db.String(255), nullable=False)  # 用户昵称
    password = db.Column(db.String(255), nullable=False)  # 用户密码
    email = db.Column(db.String(255), nullable=True)  # 用户密码
    phone = db.Column(db.String(15), nullable=True)  # 用户手机号
    access_code = db.Column(db.String(255), nullable=True)  # token
    update_time = db.Column(db.DateTime, nullable=True)  # 更新时间

class Student(db.Model):
    """
    学员表
    """
    __tablename__ = 'ht_student'
    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    name = db.Column(db.String(30), nullable=False)  # 姓名
    phone = db.Column(db.String(20), nullable=True)
    birthday = db.Column(db.String(20), nullable=True)
    age = db.Column(db.Integer, nullable=True)
    used_hour = db.Column(db.Integer, nullable=True)
    left_hour = db.Column(db.Integer, nullable=True)
    remark = db.Column(db.String(255), nullable=True)
    type = db.Column(db.Integer, nullable=True)
    status = db.Column(db.Integer, nullable=True)
    create_time = db.Column(db.DateTime, nullable=True)
    update_time = db.Column(db.DateTime, nullable=True)

class Teacher(db.Model):
    """
    教师表
    """
    __tablename__ = 'ht_teacher'
    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    name = db.Column(db.String(40), nullable=False)  # 姓名
    remark = db.Column(db.String(255), nullable=True)
    update_time = db.Column(db.DateTime, nullable=True)

    def list(self):
        return {
            "id": self.id,
            "name": self.name
        }

class Class(db.Model):
    """
    班级表
    """
    __tablename__ = 'ht_class'
    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    class_name = db.Column(db.String(200), nullable=False)
    min_num = db.Column(db.Integer, nullable=True)
    max_num = db.Column(db.Integer, nullable=True)
    total_hour = db.Column(db.Integer, nullable=True)
    teached_hour = db.Column(db.Integer, nullable=True)
    teacher_id = db.Column(db.String(200), nullable=True)
    remark = db.Column(db.String(255), nullable=True)
    begin_time = db.Column(db.DateTime, nullable=True)
    end_time = db.Column(db.DateTime, nullable=True)
    classroom = db.Column(db.String(20), nullable=True)
    status = db.Column(db.Integer, nullable=True)
    target = db.Column(db.String(30), nullable=True)
    create_time = db.Column(db.DateTime, nullable=True)
    update_time = db.Column(db.DateTime, nullable=True)

class Log(db.Model):
    """
    日志表
    """
    __tablename__ = 'ht_log'
    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    type = db.Column(db.Integer, nullable=True)
    time = db.Column(db.DateTime, nullable=True)
    teacher_id = db.Column(db.Integer, nullable=True)
    student_id = db.Column(db.Integer, nullable=True)
    class_id = db.Column(db.Integer, nullable=True)
    operator_id = db.Column(db.Integer, nullable=True)
    remark = db.Column(db.String(255), nullable=True)

class StuCls(db.Model):
    """
    学生&班级对应表
    """
    __tablename__ = 'ht_stu_cls'
    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    class_id = db.Column(db.Integer, nullable=True)
    student_id = db.Column(db.Integer, nullable=True)
class ClsWd(db.Model):
    """
    班级授课星期表
    """
    __tablename__ = 'ht_cls_wd'
    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    class_id = db.Column(db.Integer, nullable=True)
    weekday = db.Column(db.Integer, nullable=True)

class UserLoginMethod(db.Model):
    """
    用户登陆验证表
    """
    __tablename__ = 'user_login_method'
    id = db.Column(db.Integer, autoincrement=True, primary_key=True)  # 用户登陆方式主键ID
    user_id = db.Column(db.Integer, nullable=False)  # 用户主键ID
    login_method = db.Column(db.String(36), nullable=False)  # 用户登陆方式，WX微信，P手机
    identification = db.Column(db.String(36), nullable=False)  # 用户登陆标识，微信ID或手机号
    access_code = db.Column(db.String(36), nullable=True)  # 用户登陆通行码，密码或token


class Article(db.Model):
    """
    文章表
    """
    __tablename__ = 'article'
    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    title = db.Column(db.String(20), nullable=False)  # 文章标题
    body = db.Column(db.String(255), nullable=False)  # 文章内容
    last_change_time = db.Column(db.DateTime, nullable=False, default=datetime.now)  # 最后一次修改日期
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # 作者


class ChangeLogs(db.Model):
    """
    修改日志
    """
    __tablename__ = 'change_logs'
    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # 作者
    article_id = db.Column(db.Integer, db.ForeignKey('article.id'))  # 文章
    modify_content = db.Column(db.String(255), nullable=False)  # 修改内容
    create_time = db.Column(db.DateTime, nullable=False)  # 创建日期
