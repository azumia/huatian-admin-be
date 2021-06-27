from app.api.api_test import bp as bp_api_test
from app.api.api_user import bp as bp_api_user
from app.api.api_student import bp as bp_api_student
from app.api.api_teacher import bp as bp_api_teacher
from app.api.api_class import bp as bp_api_class
from app.api.api_log import bp as bp_api_log
from app.api.api_stu_cls import bp as bp_api_stu_cls
from app.api.services import ArticleAPI
from app.api.services import UserAPI

router = [
    bp_api_test,  # 接口测试
    bp_api_user,
    bp_api_student,
    bp_api_teacher,
    bp_api_class,
    bp_api_log,
    bp_api_stu_cls,
    ArticleAPI,  # 自定义MethodView
    UserAPI
]
