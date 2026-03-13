from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
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
}


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
    "1.0.0",
)
class PairItPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        config = context.get_config()
        self.whitelist = config.get("platform_settings", {}).get("id_whitelist", [])

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
