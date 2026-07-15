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
                "description": "完善学术交流资料，找到志同道合的研究伙伴。共 10 题，涵盖科研经历、研究方向与匹配偏好。",
                "questions": [
                    {"id": "research_stage", "text": "你目前的科研参与情况是？", "type": "single_choice", "required": True, "options": [{"value": "尚无经验", "label": "尚无正式科研经历，希望入门"}, {"value": "课程项目", "label": "参加过课程项目或学科竞赛"}, {"value": "实验室协助", "label": "正在实验室协助课题"}, {"value": "独立课题", "label": "正在独立或作为主要成员开展课题"}, {"value": "已有成果", "label": "已经完成论文、专利或完整研究项目"}]},
                    {"id": "academic_achievements", "text": "你目前有哪些学术成果或项目经历？", "type": "multiple_choice", "required": True, "options": [{"value": "暂无", "label": "暂无"}, {"value": "论文发表", "label": "论文发表或录用"}, {"value": "会议报告", "label": "会议报告或海报展示"}, {"value": "专利软著", "label": "专利或软件著作权"}, {"value": "科研竞赛", "label": "科研竞赛或创新项目"}, {"value": "开源项目", "label": "开源项目或数据集"}, {"value": "其他", "label": "其他"}]},
                    {"id": "research_methods", "text": "你擅长或接触过哪些研究方法？", "type": "multiple_choice", "required": True, "options": [{"value": "理论分析", "label": "理论分析"}, {"value": "实验设计", "label": "实验设计"}, {"value": "数据挖掘", "label": "数据挖掘"}, {"value": "仿真模拟", "label": "仿真模拟"}, {"value": "田野调查", "label": "田野调查"}, {"value": "统计分析", "label": "统计分析"}, {"value": "机器学习建模", "label": "机器学习建模"}, {"value": "质性研究", "label": "质性研究/访谈"}, {"value": "文献综述", "label": "文献综述"}, {"value": "其他", "label": "其他"}]},
                    {"id": "skills_tools", "text": "你掌握哪些技能或工具？", "type": "multiple_choice", "required": True, "options": [{"value": "Python", "label": "Python"}, {"value": "R", "label": "R"}, {"value": "MATLAB", "label": "MATLAB"}, {"value": "C_C++", "label": "C/C++"}, {"value": "LaTeX", "label": "LaTeX"}, {"value": "SPSS", "label": "SPSS"}, {"value": "PyTorch", "label": "PyTorch"}, {"value": "TensorFlow", "label": "TensorFlow"}, {"value": "Stata", "label": "Stata"}, {"value": "Origin", "label": "Origin/GraphPad"}, {"value": "文献管理", "label": "文献管理工具"}, {"value": "其他", "label": "其他"}]},
                    {"id": "self_assess_literature", "text": "研究能力自评：文献检索与阅读能力（1-5分）", "type": "single_choice", "required": True, "options": [{"value": "1", "label": "1"}, {"value": "2", "label": "2"}, {"value": "3", "label": "3"}, {"value": "4", "label": "4"}, {"value": "5", "label": "5"}]},
                    {"id": "self_assess_problem", "text": "研究能力自评：问题定义与研究思路（1-5分）", "type": "single_choice", "required": True, "options": [{"value": "1", "label": "1"}, {"value": "2", "label": "2"}, {"value": "3", "label": "3"}, {"value": "4", "label": "4"}, {"value": "5", "label": "5"}]},
                    {"id": "self_assess_experiment", "text": "研究能力自评：实验设计或数据分析能力（1-5分）", "type": "single_choice", "required": True, "options": [{"value": "1", "label": "1"}, {"value": "2", "label": "2"}, {"value": "3", "label": "3"}, {"value": "4", "label": "4"}, {"value": "5", "label": "5"}]},
                    {"id": "self_assess_writing", "text": "研究能力自评：论文写作与学术表达能力（1-5分）", "type": "single_choice", "required": True, "options": [{"value": "1", "label": "1"}, {"value": "2", "label": "2"}, {"value": "3", "label": "3"}, {"value": "4", "label": "4"}, {"value": "5", "label": "5"}]},
                    {"id": "self_assess_coding", "text": "研究能力自评：编程或工具使用能力（1-5分）", "type": "single_choice", "required": True, "options": [{"value": "1", "label": "1"}, {"value": "2", "label": "2"}, {"value": "3", "label": "3"}, {"value": "4", "label": "4"}, {"value": "5", "label": "5"}]},
                    {"id": "current_topic", "text": "你目前的研究课题、论文题目或项目主题是什么？", "type": "text", "required": False},
                    {"id": "learn_direction", "text": "你希望继续学习或拓展哪些领域？", "type": "multiple_choice", "required": True, "options": [{"value": "AI机器学习", "label": "AI与机器学习"}, {"value": "数据科学", "label": "数据科学"}, {"value": "生物信息", "label": "生物信息"}, {"value": "量子计算", "label": "量子计算"}, {"value": "网络安全", "label": "网络安全"}, {"value": "材料科学", "label": "材料科学"}, {"value": "环境科学", "label": "环境科学"}, {"value": "医学", "label": "医学"}, {"value": "数学", "label": "数学"}, {"value": "物理", "label": "物理"}, {"value": "化学", "label": "化学"}, {"value": "心理学", "label": "心理学"}, {"value": "社会学", "label": "社会学"}, {"value": "经济学", "label": "经济学"}, {"value": "其他", "label": "其他"}]},
                    {"id": "interdisciplinary", "text": "你希望探索哪些学科交叉方向？", "type": "text", "required": False},
                    {"id": "academic_goal", "text": "你希望通过学术交流实现什么目标？", "type": "multiple_choice", "required": True, "options": [{"value": "请教学术问题", "label": "请教学术问题"}, {"value": "交流研究思路", "label": "交流研究思路"}, {"value": "学习方法工具", "label": "学习研究方法或工具"}, {"value": "找科研伙伴", "label": "寻找科研伙伴"}, {"value": "合作论文项目", "label": "合作完成论文或项目"}, {"value": "跨学科合作", "label": "跨学科合作"}, {"value": "了解升学科研", "label": "了解实验室/升学与科研经历"}, {"value": "其他", "label": "其他"}]},
                    {"id": "match_identity", "text": "你希望匹配怎样的身份？", "type": "single_choice", "required": True, "options": [{"value": "同专业同学", "label": "同专业同学"}, {"value": "同专业前辈", "label": "同专业学长学姐/前辈"}, {"value": "跨专业互补", "label": "跨专业互补"}, {"value": "经验相近", "label": "经验相近"}, {"value": "不限", "label": "不限"}]},
                    {"id": "frequency", "text": "你希望交流的频率是？", "type": "single_choice", "required": True, "options": [{"value": "每周一次", "label": "每周一次"}, {"value": "每两周一次", "label": "每两周一次"}, {"value": "每月一次", "label": "每月一次"}, {"value": "灵活", "label": "灵活"}]},
                    {"id": "communication", "text": "你更偏向哪种交流方式？", "type": "single_choice", "required": True, "options": [{"value": "线上文字", "label": "线上文字"}, {"value": "线上语音视频", "label": "线上语音或视频"}, {"value": "线下见面", "label": "线下见面"}, {"value": "都可以", "label": "都可以"}]},
                    {"id": "available_time", "text": "你通常什么时间方便交流？（可多选）", "type": "multiple_choice", "required": True, "options": [{"value": "工作日上午", "label": "工作日上午"}, {"value": "工作日下午", "label": "工作日下午"}, {"value": "工作日晚上", "label": "工作日晚上"}, {"value": "周末", "label": "周末"}]},
                ],
            },
            {
                "slug": "daily",
                "title": "日常生活兴趣",
                "section": "daily",
                "description": "找到日常搭子。共 10 题，涵盖活动兴趣、伙伴偏好与相处方式。",
                "questions": [
                    {"id": "daily_interests", "text": "你平时感兴趣或经常参与哪些活动？", "type": "multiple_choice", "required": True, "options": [{"value": "旅行探索", "label": "旅行与城市探索"}, {"value": "运动健身", "label": "运动健身"}, {"value": "户外徒步", "label": "户外徒步/骑行"}, {"value": "游戏电竞", "label": "游戏与电竞"}, {"value": "桌游剧本", "label": "桌游/剧本娱乐"}, {"value": "影视追剧", "label": "影视与追剧"}, {"value": "音乐演出", "label": "音乐与演出"}, {"value": "阅读写作", "label": "阅读与写作"}, {"value": "摄影", "label": "摄影"}, {"value": "美食探店", "label": "美食探店"}, {"value": "展览博物馆", "label": "展览与博物馆"}, {"value": "手工创作", "label": "手工与创作"}, {"value": "宠物", "label": "宠物"}, {"value": "语言学习", "label": "语言学习"}, {"value": "志愿服务", "label": "志愿服务"}, {"value": "其他", "label": "其他"}]},
                    {"id": "core_interests", "text": "请从上述兴趣中选出你最希望找到搭子的 1-3 项", "type": "tags", "required": True},
                    {"id": "partner_type", "text": "你目前最希望认识哪类伙伴？", "type": "multiple_choice", "required": True, "options": [{"value": "长期朋友", "label": "长期稳定的朋友"}, {"value": "活动搭子", "label": "一起参加活动的搭子"}, {"value": "旅行搭子", "label": "旅行搭子"}, {"value": "运动搭子", "label": "运动搭子"}, {"value": "游戏搭子", "label": "游戏搭子"}, {"value": "学习搭子", "label": "学习/自习搭子"}, {"value": "探店搭子", "label": "探店或观展搭子"}, {"value": "线上聊天", "label": "线上聊天伙伴"}, {"value": "技能互换", "label": "技能互换伙伴"}, {"value": "其他", "label": "其他"}]},
                    {"id": "activity_frequency", "text": "你通常愿意以什么频率参加共同活动？", "type": "single_choice", "required": True, "options": [{"value": "每周多次", "label": "每周多次"}, {"value": "每周一次", "label": "每周一次左右"}, {"value": "每月1-2次", "label": "每月 1—2 次"}, {"value": "偶尔再约", "label": "偶尔，有合适活动再约"}, {"value": "线上为主", "label": "不固定，线上交流为主"}]},
                    {"id": "available_time_slots", "text": "你通常有哪些可用时间？（可多选）", "type": "multiple_choice", "required": True, "options": [{"value": "工作日上午", "label": "工作日上午"}, {"value": "工作日下午", "label": "工作日下午"}, {"value": "工作日晚上", "label": "工作日晚上"}, {"value": "周六白天", "label": "周六白天"}, {"value": "周六晚上", "label": "周六晚上"}, {"value": "周日白天", "label": "周日白天"}, {"value": "周日晚上", "label": "周日晚上"}, {"value": "寒暑假节假日", "label": "寒暑假/节假日"}, {"value": "时间灵活", "label": "时间灵活"}]},
                    {"id": "activity_area", "text": "你主要在哪些区域活动？", "type": "single_choice", "required": True, "options": [{"value": "学校附近", "label": "学校/单位附近"}, {"value": "所在区", "label": "所在区"}, {"value": "城市中心", "label": "城市中心"}, {"value": "其他", "label": "其他"}]},
                    {"id": "acceptable_range", "text": "你可接受的活动范围是？", "type": "single_choice", "required": True, "options": [{"value": "步行骑行", "label": "步行或骑行可达"}, {"value": "公交30分钟内", "label": "公交地铁 30 分钟内"}, {"value": "1小时内", "label": "1 小时内"}, {"value": "全城均可", "label": "全城均可"}, {"value": "仅线上", "label": "仅线上"}]},
                    {"id": "social_style", "text": "你更喜欢哪种相处形式？（可多选）", "type": "multiple_choice", "required": True, "options": [{"value": "一对一", "label": "一对一相处"}, {"value": "3-5人小组", "label": "3—5 人小组"}, {"value": "多人活动", "label": "多人活动"}, {"value": "线上文字", "label": "线上文字聊天"}, {"value": "线上语音游戏", "label": "线上语音/游戏"}, {"value": "线下见面", "label": "线下见面"}, {"value": "先线上再线下", "label": "先线上熟悉再线下"}, {"value": "都可以", "label": "都可以"}]},
                    {"id": "social_pace", "text": "以下哪些描述更符合你的相处节奏？（可多选）", "type": "multiple_choice", "required": True, "options": [{"value": "提前规划", "label": "喜欢提前规划"}, {"value": "随性临时", "label": "比较随性，临时约也可以"}, {"value": "主动发起", "label": "主动发起活动"}, {"value": "习惯被约", "label": "更习惯别人发起"}, {"value": "高频聊天", "label": "喜欢高频聊天"}, {"value": "低频聊天", "label": "不需要频繁聊天"}, {"value": "慢热", "label": "慢热"}, {"value": "外向健谈", "label": "外向健谈"}, {"value": "重视守时", "label": "重视守时"}, {"value": "重视空间", "label": "重视个人空间"}]},
                    {"id": "consumption_pref", "text": "你的活动消费偏好更接近哪一种？", "type": "single_choice", "required": False, "options": [{"value": "低预算", "label": "尽量低预算或免费活动"}, {"value": "性价比", "label": "更看重性价比"}, {"value": "适中", "label": "预算适中，视活动而定"}, {"value": "体验优先", "label": "体验优先，预算较灵活"}, {"value": "不参与匹配", "label": "不希望以消费偏好参与匹配"}]},
                    {"id": "daily_bio", "text": "请用几句话介绍自己，或写下希望搭子提前知道的事项。", "type": "text", "required": False},
                ],
            },
            {
                "slug": "dating",
                "title": "恋爱交友资料",
                "section": "dating",
                "description": "完善恋爱交友资料，开启匹配。共 10 题，涵盖交友目的、兴趣与价值观。",
                "questions": [
                    {"id": "dating_purpose", "text": "你使用恋爱交友板块的主要目的是什么？", "type": "single_choice", "required": True, "options": [{"value": "长期关系", "label": "希望认真发展长期关系"}, {"value": "先从朋友开始", "label": "希望先从朋友开始，合适再进一步"}, {"value": "认识人", "label": "希望认识可能合适的人，不急于确定关系"}, {"value": "随缘", "label": "目前没有明确目标，愿意慢慢了解"}]},
                    {"id": "relationship_status", "text": "请确认你目前处于可以开展新关系的状态。", "type": "single_choice", "required": True, "options": [{"value": "单身愿认识", "label": "是，我目前单身且愿意认识新的人"}, {"value": "暂时不是", "label": "暂时不是或不确定"}]},
                    {"id": "dating_location", "text": "你的现居地是？（城市＋区级范围）", "type": "text", "required": True},
                    {"id": "dating_range", "text": "你可接受的认识范围是？", "type": "single_choice", "required": True, "options": [{"value": "同校附近", "label": "同校/同单位附近"}, {"value": "同区", "label": "同区"}, {"value": "同城", "label": "同城"}, {"value": "异地也可以", "label": "异地也可以"}, {"value": "仅线上", "label": "仅线上先了解"}]},
                    {"id": "personal_intro", "text": "请用几句话介绍自己。", "type": "text", "required": False},
                    {"id": "dating_interests", "text": "你的兴趣爱好和日常生活方式有哪些？（可多选）", "type": "multiple_choice", "required": True, "options": [{"value": "运动健身", "label": "运动健身"}, {"value": "旅行", "label": "旅行"}, {"value": "游戏", "label": "游戏"}, {"value": "影视", "label": "影视"}, {"value": "音乐", "label": "音乐"}, {"value": "阅读", "label": "阅读"}, {"value": "摄影", "label": "摄影"}, {"value": "美食", "label": "美食"}, {"value": "展览", "label": "展览"}, {"value": "户外", "label": "户外"}, {"value": "宠物", "label": "宠物"}, {"value": "手工创作", "label": "手工创作"}, {"value": "其他", "label": "其他"}]},
                    {"id": "dating_mbti", "text": "你的 MBTI 是什么？", "type": "single_choice", "required": False, "options": [{"value": "INTJ", "label": "INTJ"}, {"value": "INTP", "label": "INTP"}, {"value": "ENTJ", "label": "ENTJ"}, {"value": "ENTP", "label": "ENTP"}, {"value": "INFJ", "label": "INFJ"}, {"value": "INFP", "label": "INFP"}, {"value": "ENFJ", "label": "ENFJ"}, {"value": "ENFP", "label": "ENFP"}, {"value": "ISTJ", "label": "ISTJ"}, {"value": "ISFJ", "label": "ISFJ"}, {"value": "ESTJ", "label": "ESTJ"}, {"value": "ESFJ", "label": "ESFJ"}, {"value": "ISTP", "label": "ISTP"}, {"value": "ISFP", "label": "ISFP"}, {"value": "ESTP", "label": "ESTP"}, {"value": "ESFP", "label": "ESFP"}, {"value": "未测试", "label": "还没有测试过"}, {"value": "不确定", "label": "不确定"}, {"value": "不愿填", "label": "不希望填写"}]},
                    {"id": "connection_style", "text": "你更喜欢怎样认识和保持联系？", "type": "single_choice", "required": True, "options": [{"value": "先文字聊天", "label": "先文字聊天"}, {"value": "语音视频", "label": "语音或视频"}, {"value": "尽快线下", "label": "尽快线下见面"}, {"value": "顺其自然", "label": "顺其自然"}]},
                    {"id": "chat_frequency", "text": "你希望的聊天频率是？", "type": "single_choice", "required": True, "options": [{"value": "每天较多", "label": "每天较多"}, {"value": "每天少量", "label": "每天少量"}, {"value": "每几天联系", "label": "每几天联系"}, {"value": "不固定", "label": "不固定"}]},
                    {"id": "relationship_pace", "text": "你希望的关系统奏是？", "type": "single_choice", "required": True, "options": [{"value": "慢慢了解", "label": "慢慢了解"}, {"value": "节奏适中", "label": "节奏适中"}, {"value": "较快确认", "label": "希望较快确认是否合适"}]},
                    {"id": "ideal_person_traits", "text": "你希望遇见怎样的人？（可多选）", "type": "multiple_choice", "required": True, "options": [{"value": "真诚可靠", "label": "真诚可靠"}, {"value": "善于沟通", "label": "善于沟通"}, {"value": "情绪稳定", "label": "情绪稳定"}, {"value": "有责任感", "label": "有责任感"}, {"value": "尊重边界", "label": "尊重边界"}, {"value": "共同兴趣", "label": "有共同兴趣"}, {"value": "生活积极", "label": "生活积极"}, {"value": "独立思考", "label": "有独立思考"}, {"value": "幽默有趣", "label": "幽默有趣"}, {"value": "目标感强", "label": "目标感强"}, {"value": "温和体贴", "label": "温和体贴"}, {"value": "其他", "label": "其他"}]},
                    {"id": "age_range_pref", "text": "你希望认识的对象年龄段是？", "type": "text", "required": False},
                    {"id": "family_future", "text": "关于家庭关系与未来生活，你更接近哪些想法？（可多选）", "type": "multiple_choice", "required": False, "options": [{"value": "重视原生家庭", "label": "重视双方与原生家庭保持良好关系"}, {"value": "伴侣独立空间", "label": "更重视伴侣之间的独立空间"}, {"value": "有结婚意愿", "label": "未来有结婚意愿"}, {"value": "结婚未定", "label": "未来是否结婚尚未确定"}, {"value": "希望有孩子", "label": "希望未来有孩子"}, {"value": "生育未定", "label": "是否生育尚未确定"}, {"value": "共同成长", "label": "更重视共同成长与生活质量"}, {"value": "暂不讨论", "label": "暂时不想讨论长期规划"}, {"value": "其他", "label": "其他"}]},
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

