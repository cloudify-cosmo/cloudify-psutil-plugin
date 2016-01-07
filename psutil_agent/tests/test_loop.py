import sched
import time

import mock
import testtools

from psutil_agent.loop import collect_metrics, create_scheduled_fun


class TestCollectMetrics(testtools.TestCase):
    def test_no_method_and_no_interval(self):
        with mock.patch('psutil_agent.loop.create_scheduled_fun') as m:
            collect_metrics({}, [{}])
            m.assert_not_called()

    def test_no_interval(self):
        with mock.patch('psutil_agent.loop.create_scheduled_fun') as m:
            collect_metrics({}, [{'method': 'some_method'}])
            m.assert_not_called()

    def test_no_method(self):
        with mock.patch('psutil_agent.loop.create_scheduled_fun') as m:
            collect_metrics({}, [{'interval': 2}])
            m.assert_not_called()

    def test_both_method_and_interval_present(self):
        with mock.patch('psutil_agent.loop.create_scheduled_fun') as m:
            collect_metrics({}, [{'interval': 2, 'method': 'some method'}])
            self.assertEqual(True, m.called,
                             "create_scheduled_fun() wasn't called.")


class TestCreateScheduledFun(testtools.TestCase):
    def setUp(self):
        super(TestCreateScheduledFun, self).setUp()
        self.scheduler = sched.scheduler(time.time, time.sleep)
        self.scheduler.enter = mock.MagicMock()

    def test_fail_retrieving_psutil_function(self):
        create_scheduled_fun({'broker_user': ''}, self.scheduler,
                             'inexistent_function', 0, {}, '', '')

        self.assertEqual(False, self.scheduler.enter.called)

    def test_fail_invoking_psutil_function(self):
        create_scheduled_fun({'broker_user': ''}, self.scheduler,
                             'cpu_times_percent', 0, {'test': 'a'}, '', '')

        self.assertEqual(False, self.scheduler.enter.called)

    @mock.patch('psutil_agent.loop.publish_data', return_value={})
    def test_fail_retrieving_result_argument(self, *args, **kwargs):
        create_scheduled_fun({'broker_user': ''}, self.scheduler,
                             'cpu_times_percent', 0, {}, 'test', '')

        self.assertEqual(False, self.scheduler.enter.called)

    @mock.patch('psutil_agent.loop.publish_data', return_value={})
    def test_everything_all_right(self, *args, **kwargs):
        create_scheduled_fun({'broker_user': ''}, self.scheduler,
                             'cpu_times_percent', 0, {}, 'system', '')

        self.assertEqual(True, self.scheduler.enter.called)
