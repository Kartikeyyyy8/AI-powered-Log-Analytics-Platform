import unittest

from LogProcessing.parsing.message_classifier import MessageClassifier


class MessageClassifierTests(unittest.TestCase):
    def test_classifies_stand_step_changed(self):
        msg_type, metrics = MessageClassifier.classify_and_extract("onStandStepChanged 3579")
        self.assertEqual(msg_type, "onStandStepChanged")
        self.assertEqual(metrics, {"step_count": 3579})

    def test_classifies_on_extend(self):
        msg_type, metrics = MessageClassifier.classify_and_extract("onExtend:1514038530000 14 0 4")
        self.assertEqual(msg_type, "onExtend")
        self.assertEqual(
            metrics,
            {"timestamp_ms": 1514038530000, "param_1": 14, "param_2": 0, "param_3": 4},
        )

    def test_classifies_calories_and_altitude(self):
        m1, metrics1 = MessageClassifier.classify_and_extract("calculateCaloriesWithCache totalCalories=52108")
        self.assertEqual(m1, "calculateCaloriesWithCache")
        self.assertEqual(metrics1, {"total_calories": 52108})

        m2, metrics2 = MessageClassifier.classify_and_extract("calculateAltitudeWithCache totalAltitude=60")
        self.assertEqual(m2, "calculateAltitudeWithCache")
        self.assertEqual(metrics2, {"total_altitude": 60})

    def test_classifies_report(self):
        m, metrics = MessageClassifier.classify_and_extract("REPORT : 1514038500000 10 0 10")
        self.assertEqual(m, "REPORT")
        self.assertEqual(metrics["timestamp_ms"], 1514038500000)
        self.assertEqual(metrics["v_1"], 10)

    def test_classifies_broadcast_events(self):
        m1, _ = MessageClassifier.classify_and_extract("onReceive action: android.intent.action.SCREEN_ON")
        self.assertEqual(m1, "SCREEN_ON")

        m2, _ = MessageClassifier.classify_and_extract("onReceive action: android.intent.action.SCREEN_OFF")
        self.assertEqual(m2, "SCREEN_OFF")

        m3, _ = MessageClassifier.classify_and_extract("processHandleBroadcastAction action:android.intent.action.TIME_TICK")
        self.assertEqual(m3, "TIME_TICK")

        m4, _ = MessageClassifier.classify_and_extract("onReceive action: android.intent.action.BOOT_COMPLETED")
        self.assertEqual(m4, "BOOT_COMPLETED")

    def test_classifies_try_to_reload_steps_with_pipes(self):
        m, metrics = MessageClassifier.classify_and_extract("tryToReloadTodayBasicSteps1514044800223|3786|0|0")
        self.assertEqual(m, "tryToReloadTodayBasicSteps")
        self.assertEqual(metrics["timestamp_ms"], 1514044800223)
        self.assertEqual(metrics["step_count"], 3786)

    def test_fallback_classification(self):
        m, _ = MessageClassifier.classify_and_extract("customAppFunction() result=ok")
        self.assertEqual(m, "customAppFunction")


if __name__ == "__main__":
    unittest.main()
