import asyncio

from datetime import datetime
from decimal import Decimal
from typing import TypedDict, NewType, Protocol, NotRequired, Any, Callable, Awaitable

TgMessageId = NewType("TgMessageId", int)
TgChatId = NewType("TgChatId", int)
TgUserId = NewType("TgUserId", int)
TgSenderName = NewType("TgSenderName", str)
TgSenderUsername = NewType("TgSenderUsername", str)
MessageId = NewType("MessageId", str)

# SenderId = NewType("SenderId", int)
# SenderName = NewType("SenderName", str)
# SenderUsername = NewType("SenderUsername", str)


class TelegramSender(Protocol):
    id: int
    bot: bool
    first_name: str | None
    last_name: str | None
    username: str | None


CompanyId = NewType("CompanyId", int)
CompanyName = NewType("CompanyName", str)


class Company(TypedDict):
    id: CompanyId
    name: CompanyName


NicheId = NewType("NicheId", int)
NicheName = NewType("NicheName", str)


class Niche(TypedDict):
    id: NicheId
    name: NicheName
    company_id: CompanyId
    company_name: CompanyName


class NicheWithConfig(TypedDict):
    id: NicheId
    name: str
    slug: str
    company_id: CompanyId
    company_name: str
    about: str | None
    extra_instructions: str | None
    keywords: list[str]
    blacklist: list[str]


LeadResultId = NewType("LeadResultId", int)


class LeadResult(TypedDict):
    lead_result_id: LeadResultId
    lead: bool
    niche_score: int
    intent_score: int
    description: str
    reply_author_relation: str | None

    source_link: str
    source_title: str
    text: str
    reply_text: str | None

    sender_name: str | None
    sender_username: str | None
    sender_id: TgUserId | None

    user_id: TgUserId | None
    user_link: str


class ReportCompany(TypedDict):
    id: CompanyId
    name: str


class RatedBy(TypedDict):
    id: int
    username: str | None
    name: str | None


class CompanyTgTarget(TypedDict):
    company_id: CompanyId
    chat_id: TgChatId
    metrics_topic_id: int | None
    company_name: str


class TgReplyTo(Protocol):
    reply_to_msg_id: int | None


class TgMessage(Protocol):
    id: int
    reply_to: TgReplyTo | None
    post: bool
    text: str
    date: datetime
    reply_to_msg_id: int | None
    sender_id: TgUserId


class TgEventMessage(Protocol):
    id: int
    chat_id: TgChatId | None
    message: TgMessage
    out: bool
    post: bool
    date: datetime
    reply_to_msg_id: TgMessageId | None
    text: str


class TgConfig(TypedDict):
    id: int
    company_id: CompanyId
    chat_id: TgChatId
    leads_topic_id: int
    metrics_topic_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    company_name: NotRequired[str]


class MessageWithoutEmbedding(TypedDict):
    id: MessageId
    reply_to_id: MessageId | None
    reply_sender_id: TgUserId | None
    tg_message_id: TgMessageId
    tg_chat_id: TgChatId
    text: str
    user_id: TgUserId | None
    user_link: str | None
    source_link: str | None
    tg_created_at: datetime | None
    created_at: datetime
    updated_at: datetime


class RatingData(TypedDict):
    feedback: str
    label: str
    text: str
    human_lead: bool | None


class SummaryTarget(TypedDict):
    company_id: CompanyId
    chat_id: TgChatId
    company_name: str
    metrics_topic_id: int | None


type Embedding = list[float]


class PrefilterResult(TypedDict):
    ok: bool
    reason: str | None


class IsLeadResult(TypedDict):
    lead: bool
    niche_score: int
    intent_score: int
    description: str
    reply_author_relation: str
    raw_response: dict[str, Any]
    prompt: str
    prompt_version: str


class TgUser(TypedDict):
    id: TgUserId
    bot: bool
    first_name: str | None
    last_name: str | None
    username: str | None


class DailySummaryRow(TypedDict):
    niche_id: NicheId
    niche_name: str
    company_id: CompanyId
    company_name: str

    checked: int
    leads_found: int
    rated: int
    good: int
    bad: int
    skipped: int
    spam: int

    avg_niche_score: Decimal | None
    avg_intent_score: Decimal | None

    without_reply: int
    reply_same_author: int
    reply_other_author: int
    reply_unknown_author: int

    bad_score_75_79: int
    bad_score_80_plus: int


class DailySummaryStats(TypedDict):
    niche_id: NicheId
    niche_name: str
    company_id: CompanyId
    company_name: str

    checked: int
    leads_found: int
    rated: int
    good: int
    bad: int
    skipped: int
    spam: int

    avg_niche_score: float | None
    avg_intent_score: float | None

    without_reply: int
    reply_same_author: int
    reply_other_author: int
    reply_unknown_author: int

    bad_score_75_79: int
    bad_score_80_plus: int

    lead_percent: float
    precision: float | None


class TelegramChat(Protocol):
    title: str | None
    username: str | None
    first_name: str | None


class TelegramEventMessage(Protocol):
    id: int
    post: bool
    text: str | None
    date: datetime
    reply_to_msg_id: int | None
    reply_to: TgReplyTo | None


class TelegramReplyMessage(Protocol):
    id: int
    sender_id: int | None
    text: str | None


class NewMessageEvent(Protocol):
    out: bool
    chat_id: int | None
    message: TelegramEventMessage

    def get_sender(self) -> Awaitable[TelegramSender | None]:
        ...

    def get_reply_message(
        self,
    ) -> Awaitable[TelegramReplyMessage | None]:
        ...

    def get_chat(self) -> Awaitable[TelegramChat]:
        ...


EventHandler = Callable[
    [NewMessageEvent],
    Awaitable[None],
]


class TelegramClientProtocol(Protocol):
    loop: asyncio.AbstractEventLoop

    def on(
        self,
        event_builder: object,
    ) -> Callable[[EventHandler], EventHandler]:
        ...

    def start(self) -> object:
        ...

    def run_until_disconnected(self) -> object:
        ...


class MessageData(TypedDict):
    text: str
    user_id: TgUserId | None
    user_link: str | None
    link: str | None
    tg_created_at: datetime


class MessageQueueItem(TypedDict):
    clean_text: str
    message_id: MessageId
    tg_chat_id: TgChatId
    tg_message_id: TgMessageId
    reply_tg_message_id: NotRequired[TgMessageId | None]
    reply_text: str | None
    reply_sender_id: TgUserId | None
    source_link: str
    source_title: str
    sender_id: TgUserId | None
    sender_name: str | None
    sender_username: str | None
    sender: TgUser | None
    created_at: datetime
    enqueued_at: datetime


class ProcessMessageResult(TypedDict):
    lead_result_id: LeadResultId
    lead: bool
    niche_score: int
    intent_score: int
    description: str
    reply_author_relation: str | None

    user_id: NotRequired[TgUserId | None]
    user_link: NotRequired[str]

    source_link: NotRequired[str]
    source_title: NotRequired[str]
    text: NotRequired[str]
    reply_text: NotRequired[str | None]

    sender_id: TgUserId | None
    sender_name: str | None
    sender_username: str | None


class SavedLeadResult(TypedDict):
    id: LeadResultId


class NicheConfigRow(TypedDict):
    id: NicheId
    name: str
    slug: str
    company_id: CompanyId
    company_name: str
    about: str | None
    extra_instructions: str | None


class PhraseRow(TypedDict):
    phrase: str