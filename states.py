from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class SignalStates(StatesGroup):
    choosing_market = State()
    choosing_pair = State()
    choosing_expiry = State()
    analyzing = State()


class AnalysisStates(StatesGroup):
    choosing_market = State()
    choosing_pair = State()
    choosing_expiry = State()


class AdminStates(StatesGroup):
    waiting_blacklist_reason = State()


class OwnerStates(StatesGroup):
    waiting_message_text = State()
    waiting_candle_count = State()
    waiting_candle_duration = State()
    waiting_broadcast_text = State()
