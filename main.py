import astrbot.api.message_components as components
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
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
    "pairit",
    "GamerNoTitle",
    "自动匹配群友发送的括号，这下括号再也不会出现不成对的情况了",
    "1.0.0",
)
class PairIt(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    async def initialize(self):
        logger.info("[+] PairIt has been initialized.")

    async def terminate(self):
        logger.info("[-] PairIt has been terminated.")

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def on_message(self, event: AstrMessageEvent):
        """从监听的消息中获取发送的内容，并自动匹配括号"""
        stack = Stack()
        content = event.message_obj.message_str
        msg_id = event.message_obj.message_id
        logger.debug(f"[*] Received message: {content}")
        for char in content:
            if char in PAIR_LIST:
                if stack.is_empty() or stack.data[-1] != PAIR_LIST[char]:
                    stack.push(char)
                else:
                    stack.pop()

        if not stack.is_empty():
            reply_chain = []
            missing_brackets = "".join(
                [PAIR_LIST[char] for char in reversed(stack.data)]
            )
            logger.debug(f"[*] Missing brackets: {missing_brackets}")
            reply_chain.append(components.Reply(id=msg_id, chain=[content]))
            reply_chain.append(components.Plain(missing_brackets))
            await event.send(event.chain_result(reply_chain))
        else:
            logger.debug("[*] Brackets are already paired.")
            event.stop_event()
