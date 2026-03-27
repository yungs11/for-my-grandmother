"""
할머니 말벗 AI Agent - 하드웨어 제어
터치 센서 (GPIO) + LED 상태 표시
라즈베리파이 전용 (데스크톱에서는 키보드 입력으로 시뮬레이션)
"""
from __future__ import annotations

import logging
import time
import threading
from typing import Callable

from config.settings import TOUCH_SENSOR_PIN, LED_PIN, DEBOUNCE_TIME

logger = logging.getLogger(__name__)

# GPIO 사용 가능 여부 체크
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    logger.info("RPi.GPIO 사용 불가 → 키보드 시뮬레이션 모드")


class HardwareController:
    """
    하드웨어 제어 클래스
    - 라즈베리파이: GPIO 터치 센서 + LED
    - 데스크톱: 키보드 입력으로 시뮬레이션
    """

    def __init__(self):
        self._on_touch_callback: Callable | None = None
        self._running = False
        self._thread: threading.Thread | None = None

        if GPIO_AVAILABLE:
            self._setup_gpio()

    # ─────────────────────────────────────────
    # GPIO 설정
    # ─────────────────────────────────────────
    def _setup_gpio(self):
        """라즈베리파이 GPIO 초기화"""
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(TOUCH_SENSOR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.setup(LED_PIN, GPIO.OUT)
        GPIO.output(LED_PIN, GPIO.LOW)
        logger.info("GPIO 초기화 완료 (터치: BCM %d, LED: BCM %d)",
                     TOUCH_SENSOR_PIN, LED_PIN)

    # ─────────────────────────────────────────
    # 터치 감지
    # ─────────────────────────────────────────
    def on_touch(self, callback: Callable):
        """터치 이벤트 콜백 등록"""
        self._on_touch_callback = callback

    def start_listening(self):
        """터치 센서 감지 시작"""
        self._running = True

        if GPIO_AVAILABLE:
            # GPIO 인터럽트 기반 감지
            GPIO.add_event_detect(
                TOUCH_SENSOR_PIN,
                GPIO.RISING,
                callback=self._gpio_touch_handler,
                bouncetime=int(DEBOUNCE_TIME * 1000),
            )
            logger.info("GPIO 터치 센서 감지 시작")
        else:
            # 키보드 시뮬레이션 (데스크톱 개발용)
            self._thread = threading.Thread(
                target=self._keyboard_simulation, daemon=True
            )
            self._thread.start()
            logger.info("키보드 시뮬레이션 모드 시작 (Enter 키로 터치 시뮬레이션)")

    def stop_listening(self):
        """터치 센서 감지 중지"""
        self._running = False
        if GPIO_AVAILABLE:
            GPIO.remove_event_detect(TOUCH_SENSOR_PIN)

    def _gpio_touch_handler(self, channel):
        """GPIO 인터럽트 콜백"""
        if self._on_touch_callback:
            logger.info("터치 감지! (GPIO %d)", channel)
            self._on_touch_callback()

    def _keyboard_simulation(self):
        """키보드 Enter로 터치 시뮬레이션"""
        while self._running:
            try:
                input()  # Enter 대기
                if self._on_touch_callback and self._running:
                    logger.info("터치 시뮬레이션 (Enter 키)")
                    self._on_touch_callback()
            except EOFError:
                break

    # ─────────────────────────────────────────
    # LED 제어
    # ─────────────────────────────────────────
    def led_on(self):
        """LED 켜기 (대화 중)"""
        if GPIO_AVAILABLE:
            GPIO.output(LED_PIN, GPIO.HIGH)
        logger.debug("LED ON")

    def led_off(self):
        """LED 끄기 (대기 중)"""
        if GPIO_AVAILABLE:
            GPIO.output(LED_PIN, GPIO.LOW)
        logger.debug("LED OFF")

    def led_blink(self, times: int = 3, interval: float = 0.3):
        """LED 깜빡임 (이벤트 알림)"""
        def _blink():
            for _ in range(times):
                self.led_on()
                time.sleep(interval)
                self.led_off()
                time.sleep(interval)

        threading.Thread(target=_blink, daemon=True).start()

    # ─────────────────────────────────────────
    # 정리
    # ─────────────────────────────────────────
    def cleanup(self):
        """리소스 정리"""
        self.stop_listening()
        if GPIO_AVAILABLE:
            GPIO.cleanup()
            logger.info("GPIO 정리 완료")


class TextInputSimulator:
    """
    텍스트 입력 시뮬레이터
    마이크 대신 키보드로 직접 텍스트를 입력하여 테스트
    """

    def get_input(self) -> str | None:
        """키보드에서 텍스트 입력 받기"""
        try:
            text = input("할머니 (텍스트 입력): ").strip()
            if text.lower() in ("quit", "exit", "종료"):
                return None
            return text if text else None
        except (EOFError, KeyboardInterrupt):
            return None
