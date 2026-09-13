import threading,time,unittest
from companion.awake import AwakeGuard,CONTINUOUS,SYSTEM_REQUIRED,start_receiver_guard

class AwakeTests(unittest.TestCase):
    def wait_for_active(self,guard):
        deadline=time.monotonic()+2
        while not guard.status()['active'] and time.monotonic()<deadline:
            time.sleep(.005)
        self.assertTrue(guard.status()['active'])

    def test_acquire_and_release_on_same_thread_without_display_or_away_mode(self):
        calls=[];guard=AwakeGuard(lambda flags:calls.append((threading.get_ident(),flags)),60)
        guard.start();self.assertTrue(guard.status()['active']);guard.close()
        self.assertEqual([f for _,f in calls],[CONTINUOUS|SYSTEM_REQUIRED,CONTINUOUS])
        self.assertEqual(len({tid for tid,_ in calls}),1);self.assertFalse(guard.status()['active'])

    def test_failed_request_is_reported_and_can_recover(self):
        calls=[];recovered=threading.Event()
        def apply(flags):
            calls.append(flags)
            if len(calls)==1:raise OSError('injected')
            if flags&SYSTEM_REQUIRED:recovered.set()
        guard=AwakeGuard(apply,.1);guard.start()
        self.assertFalse(guard.status()['active']);self.assertEqual(guard.status()['error'],'OSError')
        self.assertTrue(recovered.wait(2));self.wait_for_active(guard);guard.close()

    def test_duplicate_start_and_close_do_not_create_another_owner(self):
        calls=[];guard=AwakeGuard(calls.append,60);guard.start();guard.start();guard.close();guard.close()
        self.assertEqual(calls,[CONTINUOUS|SYSTEM_REQUIRED,CONTINUOUS])

    def test_close_before_start_does_not_acquire_system_requirement(self):
        calls=[];guard=AwakeGuard(calls.append,60);guard.close()
        with self.assertRaises(RuntimeError):guard.start()
        self.assertEqual(calls,[])

    def test_restart_after_close_is_explicitly_rejected(self):
        guard=AwakeGuard(lambda flags:None,60);guard.start();guard.close()
        with self.assertRaises(RuntimeError):guard.start()
        self.assertTrue(guard.status()['closed']);self.assertFalse(guard.status()['active'])

    def test_windows_failure_code_is_retained_then_cleared_on_recovery(self):
        calls=[];event=threading.Event()
        def apply(flags):
            calls.append(flags)
            if len(calls)==1:raise OSError(5,'injected, not evidence of a real policy')
            if flags&SYSTEM_REQUIRED:event.set()
        guard=AwakeGuard(apply,.1);guard.start();self.assertEqual(guard.status()['errorCode'],5)
        self.assertTrue(event.wait(2));self.wait_for_active(guard);self.assertIsNone(guard.status()['errorCode']);guard.close()

    def test_real_receiver_start_and_simulation_have_distinct_power_effects(self):
        calls=[]
        class Fake:
            def __init__(self):calls.append('created')
            def start(self):calls.append('started')
        self.assertIsNone(start_receiver_guard(True,Fake));self.assertEqual(calls,[])
        self.assertIsInstance(start_receiver_guard(False,Fake),Fake);self.assertEqual(calls,['created','started'])

    def test_close_during_slow_apply_returns_bounded_then_releases_same_owner(self):
        entered=threading.Event();release=threading.Event();calls=[]
        def apply(flags):
            calls.append((threading.get_ident(),flags))
            if flags&SYSTEM_REQUIRED:entered.set();release.wait(5)
        guard=AwakeGuard(apply,60);starter=threading.Thread(target=guard.start);starter.start()
        try:
            self.assertTrue(entered.wait(1));before=time.monotonic();guard.close()
            self.assertLess(time.monotonic()-before,2.8);self.assertTrue(guard.status()['closed'])
            self.assertFalse(guard.status()['active'])
            with self.assertRaises(RuntimeError):guard.start()
        finally:
            release.set();starter.join(3);guard.close()
        self.assertFalse(guard.thread.is_alive());self.assertFalse(guard.status()['active'])
        self.assertEqual([flags for _,flags in calls],[CONTINUOUS|SYSTEM_REQUIRED,CONTINUOUS])
        self.assertEqual(len({tid for tid,_ in calls}),1)

if __name__=='__main__':unittest.main()
