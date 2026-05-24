from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from app.bot.commands_registry import (
    BTN_ANALYSIS,
    BTN_DREAM,
    BTN_HELP,
    BTN_INSIGHTS,
    BTN_PERSONALITY,
    BTN_REPORT,
    BTN_STOIC,
    BTN_THOUGHT,
)


def rating_keyboard(prefix: str) -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(text=str(i), callback_data=f"{prefix}:{i}") for i in range(1, 11)
    ]
    rows = [buttons[i : i + 5] for i in range(0, 10, 5)]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def yes_no_keyboard(prefix: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Evet", callback_data=f"{prefix}:yes"),
                InlineKeyboardButton(text="Hayır", callback_data=f"{prefix}:no"),
            ]
        ]
    )


def checkin_start_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Rapor ver", callback_data="checkin:start")]
        ]
    )


def skip_keyboard(prefix: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Atla", callback_data=f"{prefix}:skip")]]
    )


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_REPORT), KeyboardButton(text=BTN_INSIGHTS)],
            [KeyboardButton(text=BTN_ANALYSIS), KeyboardButton(text=BTN_DREAM)],
            [KeyboardButton(text=BTN_STOIC), KeyboardButton(text=BTN_THOUGHT)],
            [KeyboardButton(text=BTN_PERSONALITY), KeyboardButton(text=BTN_HELP)],
        ],
        resize_keyboard=True,
    )
