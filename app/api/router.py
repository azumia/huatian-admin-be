from app.api.api_test import bp as bp_api_test
from app.api.api_user import bp as bp_api_user
from app.api.services import ArticleAPI
from app.api.services import UserAPI

router = [
    bp_api_test,  # 接口测试
    bp_api_user,
    ArticleAPI,  # 自定义MethodView
    UserAPI
]
