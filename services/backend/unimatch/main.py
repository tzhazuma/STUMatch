"""FastAPI application entrypoint."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from unimatch.config import get_settings
from unimatch.database import init_db
from unimatch.routers import (
    admin,
    ai,
    auth,
    chat,
    discovery,
    friends,
    matches,
    message_board,
    profiles,
    questionnaires,
    reports,
    users,
    ws,
)

logger = logging.getLogger(__name__)
settings = get_settings()

if not settings.SECRET_KEY:
    raise RuntimeError("❌ 必须设置 SECRET_KEY！请在 .env 里配置")


async def seed_questionnaires() -> None:
    """Seed default questionnaires if none exist."""
    from sqlalchemy import select
    from unimatch.database import async_session_maker
    from unimatch.models import Questionnaire

    async with async_session_maker() as db:
        existing = await db.execute(select(Questionnaire).limit(1))
        if existing.scalar_one_or_none():
            return

        questionnaires = [
            {
                "slug": "basic",
                "title": "基础资料问卷",
                "section": "global",
                "description": "帮助我们了解你，用于匹配和推荐。",
                "questions": [
                    {"id": "gender", "text": "性别", "type": "single_choice", "required": True, "options": [{"value": "male", "label": "男"}, {"value": "female", "label": "女"}, {"value": "other", "label": "其他"}]},
                    {"id": "birth_date", "text": "出生日期", "type": "date", "required": False},
                    {"id": "education_level", "text": "学历", "type": "single_choice", "required": True, "options": [{"value": "undergraduate", "label": "本科"}, {"value": "master", "label": "硕士"}, {"value": "phd", "label": "博士"}, {"value": "other", "label": "其他"}]},
                    {"id": "major", "text": "专业", "type": "text", "required": True},
                    {"id": "interests", "text": "兴趣爱好（多个用逗号分隔）", "type": "tags", "required": True},
                    {"id": "mbti", "text": "MBTI", "type": "single_choice", "required": False, "options": [{"value": "INTJ", "label": "INTJ"}, {"value": "INTP", "label": "INTP"}, {"value": "ENTJ", "label": "ENTJ"}, {"value": "ENTP", "label": "ENTP"}, {"value": "INFJ", "label": "INFJ"}, {"value": "INFP", "label": "INFP"}, {"value": "ENFJ", "label": "ENFJ"}, {"value": "ENFP", "label": "ENFP"}, {"value": "ISTJ", "label": "ISTJ"}, {"value": "ISFJ", "label": "ISFJ"}, {"value": "ESTJ", "label": "ESTJ"}, {"value": "ESFJ", "label": "ESFJ"}, {"value": "ISTP", "label": "ISTP"}, {"value": "ISFP", "label": "ISFP"}, {"value": "ESTP", "label": "ESTP"}, {"value": "ESFP", "label": "ESFP"}]},
                    {"id": "location", "text": "现居地", "type": "text", "required": False},
                    {"id": "bio", "text": "个人介绍", "type": "text", "required": False},
                ],
            },
            {
                "slug": "academic",
                "title": "学术交流资料",
                "section": "academic",
                "description": "完善学术交流资料，找到志同道合的研究伙伴。共 20 题，涵盖研究经验、兴趣方向、匹配偏好与个人偏好。",
                "questions": [
                    {"id": "has_publication", "text": "是否有论文发表经历？", "type": "single_choice", "required": True, "options": [{"value": "是", "label": "是"}, {"value": "否", "label": "否"}]},
                    {"id": "publication_count", "text": "如有论文发表，发表了几篇？", "type": "single_choice", "required": False, "options": [{"value": "1篇", "label": "1篇"}, {"value": "2-3篇", "label": "2-3篇"}, {"value": "4篇及以上", "label": "4篇及以上"}]},
                    {"id": "research_methods", "text": "你擅长的研究方法", "type": "multiple_choice", "required": True, "options": [{"value": "理论分析", "label": "理论分析"}, {"value": "实验设计", "label": "实验设计"}, {"value": "数据挖掘", "label": "数据挖掘"}, {"value": "仿真模拟", "label": "仿真模拟"}, {"value": "田野调查", "label": "田野调查"}, {"value": "统计分析", "label": "统计分析"}, {"value": "机器学习建模", "label": "机器学习建模"}, {"value": "其他", "label": "其他"}]},
                    {"id": "skills_tools", "text": "你掌握的技能/工具", "type": "multiple_choice", "required": True, "options": [{"value": "Python", "label": "Python"}, {"value": "R", "label": "R"}, {"value": "MATLAB", "label": "MATLAB"}, {"value": "C++", "label": "C++"}, {"value": "LaTeX", "label": "LaTeX"}, {"value": "SPSS", "label": "SPSS"}, {"value": "PyTorch", "label": "PyTorch"}, {"value": "TensorFlow", "label": "TensorFlow"}, {"value": "其他", "label": "其他"}]},
                    {"id": "literature_reading", "text": "文献阅读能力自评（1-5分）", "type": "single_choice", "required": True, "options": [{"value": "1", "label": "1"}, {"value": "2", "label": "2"}, {"value": "3", "label": "3"}, {"value": "4", "label": "4"}, {"value": "5", "label": "5"}]},
                    {"id": "experiment_design", "text": "实验设计能力自评（1-5分）", "type": "single_choice", "required": True, "options": [{"value": "1", "label": "1"}, {"value": "2", "label": "2"}, {"value": "3", "label": "3"}, {"value": "4", "label": "4"}, {"value": "5", "label": "5"}]},
                    {"id": "paper_writing", "text": "论文写作能力自评（1-5分）", "type": "single_choice", "required": True, "options": [{"value": "1", "label": "1"}, {"value": "2", "label": "2"}, {"value": "3", "label": "3"}, {"value": "4", "label": "4"}, {"value": "5", "label": "5"}]},
                    {"id": "coding_ability", "text": "代码能力自评（1-5分）", "type": "single_choice", "required": True, "options": [{"value": "1", "label": "1"}, {"value": "2", "label": "2"}, {"value": "3", "label": "3"}, {"value": "4", "label": "4"}, {"value": "5", "label": "5"}]},
                    {"id": "current_topic", "text": "你目前的研究课题/论文题目", "type": "text", "required": False},
                    {"id": "learn_direction", "text": "你希望拓展/学习的方向", "type": "text", "required": True},
                    {"id": "hot_interests", "text": "你感兴趣的热门领域", "type": "multiple_choice", "required": True, "options": [{"value": "AI与机器学习", "label": "AI与机器学习"}, {"value": "数据科学", "label": "数据科学"}, {"value": "生物信息", "label": "生物信息"}, {"value": "量子计算", "label": "量子计算"}, {"value": "网络安全", "label": "网络安全"}, {"value": "材料科学", "label": "材料科学"}, {"value": "环境科学", "label": "环境科学"}, {"value": "医学", "label": "医学"}, {"value": "数学", "label": "数学"}, {"value": "物理", "label": "物理"}, {"value": "化学", "label": "化学"}, {"value": "心理学", "label": "心理学"}, {"value": "社会学", "label": "社会学"}, {"value": "经济学", "label": "经济学"}, {"value": "其他", "label": "其他"}]},
                    {"id": "interdisciplinary", "text": "你希望交流的学科交叉方向", "type": "text", "required": False},
                    {"id": "match_identity", "text": "你希望匹配什么身份的人", "type": "multiple_choice", "required": True, "options": [{"value": "同专业同学", "label": "同专业同学"}, {"value": "同专业学长学姐/前辈", "label": "同专业学长学姐/前辈"}, {"value": "跨专业互补", "label": "跨专业互补"}, {"value": "导师级别", "label": "导师级别"}]},
                    {"id": "match_purpose", "text": "你希望匹配的目的", "type": "multiple_choice", "required": True, "options": [{"value": "一起合作写论文", "label": "一起合作写论文"}, {"value": "指导实验方法", "label": "指导实验方法"}, {"value": "交流研究思路", "label": "交流研究思路"}, {"value": "请教学术问题", "label": "请教学术问题"}, {"value": "找科研伙伴", "label": "找科研伙伴"}, {"value": "跨学科合作", "label": "跨学科合作"}]},
                    {"id": "frequency", "text": "你希望交流的频率", "type": "single_choice", "required": True, "options": [{"value": "每周1次", "label": "每周1次"}, {"value": "每两周1次", "label": "每两周1次"}, {"value": "每月1次", "label": "每月1次"}, {"value": "灵活", "label": "灵活"}]},
                    {"id": "communication", "text": "你更偏向哪种交流方式", "type": "single_choice", "required": True, "options": [{"value": "线上文字", "label": "线上文字"}, {"value": "线上视频", "label": "线上视频"}, {"value": "线下见面", "label": "线下见面"}, {"value": "都可以", "label": "都可以"}]},
                    {"id": "available_time", "text": "你的可用时间段", "type": "multiple_choice", "required": True, "options": [{"value": "工作日上午", "label": "工作日上午"}, {"value": "下午", "label": "下午"}, {"value": "晚上", "label": "晚上"}, {"value": "周末", "label": "周末"}]},
                    {"id": "partner_count", "text": "你希望匹配多少位伙伴", "type": "single_choice", "required": True, "options": [{"value": "1-2位", "label": "1-2位"}, {"value": "3-5位", "label": "3-5位"}, {"value": "不限", "label": "不限"}]},
                    {"id": "english_ability", "text": "你的英语能力", "type": "single_choice", "required": True, "options": [{"value": "可阅读英文文献", "label": "可阅读英文文献"}, {"value": "可用英语交流", "label": "可用英语交流"}, {"value": "只能阅读", "label": "只能阅读"}, {"value": "英语+中文均可", "label": "英语+中文均可"}]},
                    {"id": "special_needs", "text": "你有什么特别的需求或说明", "type": "text", "required": False},
                ],
            },
            {
                "slug": "daily",
                "title": "日常生活兴趣",
                "section": "daily",
                "description": "找到日常搭子。",
                "questions": [
                    {"id": "daily_interests", "text": "你感兴趣的日常活动", "type": "multiple_choice", "required": True, "options": [{"value": "运动", "label": "运动"}, {"value": "游戏", "label": "游戏"}, {"value": "旅行", "label": "旅行"}, {"value": "美食", "label": "美食"}, {"value": "摄影", "label": "摄影"}, {"value": "音乐", "label": "音乐"}, {"value": "电影", "label": "电影"}]},
                    {"id": "activity_time", "text": "通常活跃时间", "type": "single_choice", "required": False, "options": [{"value": "早晨", "label": "早晨"}, {"value": "下午", "label": "下午"}, {"value": "晚上", "label": "晚上"}, {"value": "深夜", "label": "深夜"}]},
                ],
            },
            {
                "slug": "dating",
                "title": "恋爱交友资料",
                "section": "dating",
                "description": "完善恋爱交友资料，开启匹配。",
                "questions": [
                    {"id": "dating_purpose", "text": "交友目的", "type": "single_choice", "required": True, "options": [{"value": "恋爱", "label": "恋爱"}, {"value": "交友", "label": "交友"}, {"value": "结婚", "label": "结婚"}, {"value": "随缘", "label": "随缘"}]},
                    {"id": "mbti", "text": "MBTI", "type": "single_choice", "required": False, "options": [{"value": "INTJ", "label": "INTJ"}, {"value": "INTP", "label": "INTP"}, {"value": "ENTJ", "label": "ENTJ"}, {"value": "ENTP", "label": "ENTP"}, {"value": "INFJ", "label": "INFJ"}, {"value": "INFP", "label": "INFP"}, {"value": "ENFJ", "label": "ENFJ"}, {"value": "ENFP", "label": "ENFP"}, {"value": "ISTJ", "label": "ISTJ"}, {"value": "ISFJ", "label": "ISFJ"}, {"value": "ESTJ", "label": "ESTJ"}, {"value": "ESFJ", "label": "ESFJ"}, {"value": "ISTP", "label": "ISTP"}, {"value": "ISFP", "label": "ISFP"}, {"value": "ESTP", "label": "ESTP"}, {"value": "ESFP", "label": "ESFP"}]},
                    {"id": "interests", "text": "兴趣爱好（逗号分隔）", "type": "tags", "required": True},
                    {"id": "personal_intro", "text": "个人介绍", "type": "text", "required": False},
                    {"id": "ideal_person", "text": "想遇见的人", "type": "text", "required": False},
                    {"id": "family_status", "text": "家庭状况（选填）", "type": "text", "required": False},
                ],
            },
        ]
        for q in questionnaires:
            db.add(Questionnaire(**q))
        await db.commit()
        logger.info("Seeded %d questionnaires", len(questionnaires))


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await seed_questionnaires()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(profiles.router)
app.include_router(discovery.router)
app.include_router(questionnaires.router)
app.include_router(matches.router)
app.include_router(friends.router)
app.include_router(chat.router)
app.include_router(message_board.router)
app.include_router(reports.router)
app.include_router(admin.router)
app.include_router(ai.router)
app.include_router(ws.router)


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.exception("Unhandled exception")
    return JSONResponse(status_code=500, content={"error": "internal_error", "message": str(exc)})
