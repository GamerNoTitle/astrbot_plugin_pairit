import os
import json
from pydantic import BaseModel, Field

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.core.utils.astrbot_path import get_astrbot_data_path
from astrbot.api import logger

PAIR_LIST = {
    "(": ")",
    ")": "(",
    "[": "]",
    "]": "[",
    "{": "}",
    "}": "{",
    "<": ">",
    ">": "<",
    "「": "」",
    "」": "「",
    "（": "）",
    "）": "（",
    "【": "】",
    "】": "【",
    "《": "》",
    "》": "《",
    "『": "』",
    "』": "『",
    "［": "］",
    "］": "［",
    "｛": "｝",
    "｝": "｛",
    "〈": "〉",
    "〉": "〈",
    "⟨": "⟩",
    "⟩": "⟨",
}

ABOUT_MSG = """[PairIt Plugin]
自动匹配群友发送的括号，这下括号再也不会出现不成对的情况了

- /pairit about: 显示此帮助信息
- /pairit <enable/disable> <me/group>: 在 自己(默认)/本群 启用/禁用 PairIt 插件
- /pairit status: 显示 PairIt 插件在本群和自己身上的启用状态

Github: https://github.com/GamerNoTitle/astrbot_plugin_pairit
"""


class Config(BaseModel):
    blacklist_groups: list[int | str] = Field(
        default_factory=list,
        description="不启用 PairIt 的群号码列表",
    )
    blacklist_users: list[int | str] = Field(
        default_factory=list,
        description="不启用 PairIt 的 QQ 用户号码列表",
    )


class Stack:
    """
    栈，用于压括号
    """

    def __init__(self):
        self.data = []

    def push(self, item: str):
        self.data.append(item)

    def pop(self) -> str:
        if self.is_empty():
            raise IndexError("Nothing in stack.")
        return self.data.pop()

    def is_empty(self) -> bool:
        return len(self.data) == 0

    def clear(self):
        self.data.clear()


@register(
    "PairIt",
    "GamerNoTitle",
    "自动匹配群友发送的括号，这下括号再也不会出现不成对的情况了",
    "1.2.0",
)
class PairItPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        config = context.get_config()
        self.whitelist = config.get("platform_settings", {}).get("id_whitelist", [])
        self.config_dir = get_astrbot_data_path() + "/plugin_data/astrbot_plugin_pairit"
        self.config_path = os.path.join(self.config_dir, "config.json")
        if os.path.exists(self.config_path):
            with open(self.config_path, "r", encoding="utf-8") as f:
                self.config = Config.model_validate(json.load(f))
        else:
            self.config = Config()
            self.save_config()

    def save_config(self):
        os.makedirs(self.config_dir, exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.config.model_dump(), f, ensure_ascii=False, indent=4)

    async def initialize(self):
        logger.info(
            f"[PairIt] [+] PairIt has been initialized. Whitelist: {self.whitelist}"
        )

    async def terminate(self):
        logger.info("[PairIt] [-] PairIt has been terminated.")

    @filter.event_message_type(filter.EventMessageType.GROUP_MESSAGE)
    async def on_group_message(self, event: AstrMessageEvent):
        """从监听的消息中获取发送的内容，并自动匹配括号"""
        stack = Stack()
        content = event.message_obj.message_str
        group_id = event.message_obj.group_id
        if group_id not in self.whitelist:
            logger.info(
                f"[PairIt] [*] Received message from group {group_id}, which is not in the whitelist. Ignoring."
            )
            return
        if group_id in self.config.blacklist_groups:
            logger.info(
                f"[PairIt] [*] Received message from group {group_id}, which is in the blacklist. Ignoring."
            )
            return
        if event.message_obj.sender in self.config.blacklist_users:
            logger.info(
                f"[PairIt] [*] Received message from user {event.message_obj.sender}, who is in the blacklist. Ignoring."
            )
            return
        logger.debug(f"[PairIt] [*] Received message: {content}")
        for char in content:
            if char in PAIR_LIST:
                if stack.is_empty() or stack.data[-1] != PAIR_LIST[char]:
                    stack.push(char)
                else:
                    stack.pop()

        if not stack.is_empty():
            missing_brackets = "".join(
                [PAIR_LIST[char] for char in reversed(stack.data)]
            )
            logger.debug(f"[PairIt] [*] Missing brackets: {missing_brackets}")
            logger.debug(f"[PairIt] [*] Sending plain reply: {missing_brackets}...")
            yield event.plain_result(missing_brackets)
            logger.info(f"[PairIt] [*] Successfully paired brackets.")
        else:
            logger.info(
                "[PairIt] [*] Brackets are already paired or no brackets found."
            )

    @filter.command_group("pairit")
    async def pairit(self):
        pass

    @pairit.command("about")
    async def about_command(self, event: AstrMessageEvent):
        yield event.plain_result(ABOUT_MSG)

    @pairit.command("enable")
    async def enable_command(self, event: AstrMessageEvent, whom: str = "me"):
        if whom == "me":
            # 启用自己
            user_id = event.message_obj.sender.user_id
            if user_id in self.config.blacklist_users:
                self.config.blacklist_users.remove(user_id)
                self.save_config()
                yield event.plain_result("[PairIt] 已为你启用 PairIt 插件。")
            else:
                yield event.plain_result("[PairIt] 你已经启用 PairIt 插件了哦。")
        elif whom == "group":
            # 启用本群
            group_id = event.message_obj.group_id
            if not group_id:
                return
            if group_id in self.config.blacklist_groups:
                self.config.blacklist_groups.remove(group_id)
                self.save_config()
                yield event.plain_result("[PairIt] 已为本群启用 PairIt 插件。")
            else:
                yield event.plain_result("[PairIt] 本群已经启用 PairIt 插件了哦。")
        else:
            yield event.plain_result(
                "[PairIt] 无效的命令参数，请使用 /pairit about 查看帮助信息。"
            )

    @pairit.command("disable")
    async def disable_command(self, event: AstrMessageEvent, whom: str = "me"):
        if whom == "me":
            # 禁用自己
            user_id = event.message_obj.sender.user_id
            if user_id not in self.config.blacklist_users:
                self.config.blacklist_users.append(user_id)
                self.save_config()
                yield event.plain_result("[PairIt] 已为你禁用 PairIt 插件。")
            else:
                yield event.plain_result("[PairIt] 你已经禁用 PairIt 插件了哦。")
        elif whom == "group":
            # 禁用本群
            group_id = event.message_obj.group_id
            if not group_id:
                return
            if group_id not in self.config.blacklist_groups:
                self.config.blacklist_groups.append(group_id)
                self.save_config()
                yield event.plain_result("[PairIt] 已为本群禁用 PairIt 插件。")
            else:
                yield event.plain_result("[PairIt] 本群已经禁用 PairIt 插件了哦。")
        else:
            yield event.plain_result(
                "[PairIt] 无效的命令参数，请使用 /pairit about 查看帮助信息。"
            )

    @pairit.command("status")
    async def status_command(self, event: AstrMessageEvent):
        group_id = event.message_obj.group_id
        user_id = event.message_obj.sender
        group_status = (
            "启用" if group_id not in self.config.blacklist_groups else "禁用"
        )
        user_status = "启用" if user_id not in self.config.blacklist_users else "禁用"
        yield event.plain_result(
            f"[PairIt] 插件状态：\n- 本群: {group_status}\n- 你: {user_status}"
        )
