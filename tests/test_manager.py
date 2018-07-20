from os import path

from unittest.mock import ANY, Mock
from niocore.core.context import CoreContext
from nio.modules.web import RESTHandler
from niocore.util.environment import NIOEnvironment
from niocore.testing.test_case import NIOCoreTestCase

from ..manager import ProjectManager
from niocore.core.hooks import CoreHooks
from nio.testing.condition import ConditionWaiter
from threading import Event


class TestProjectManager(NIOCoreTestCase):

    def setUp(self):

        # save previous environment
        self._saved_root = NIOEnvironment._root
        self._saved_conf_files = NIOEnvironment._conf_files

        # override NIO environment before Settings module is initialized
        self._root_path = path.join(
            path.dirname(path.abspath(path.realpath(__file__))),
            'project_path')
        NIOEnvironment.set_environment(self._root_path, ['nio.conf'])

        super().setUp()

    def tearDown(self):

        # restore previous environment
        NIOEnvironment._root = self._saved_root
        NIOEnvironment._conf_files = self._saved_conf_files

        super().tearDown()

    def test_start(self):
        # Test a handler is created and passed to REST Manager on start
        rest_manager = Mock()
        rest_manager.add_web_handler = Mock()

        context = CoreContext([], [])
        project_manager = ProjectManager()
        project_manager.get_dependency = Mock(return_value=rest_manager)
        project_manager.configure(context)

        project_manager.start()
        rest_manager.add_web_handler.assert_called_with(ANY)
        self.assertEqual(2, len(rest_manager.add_web_handler.call_args))
        self.assertTrue(
            isinstance(rest_manager.add_web_handler.call_args[0][0],
                       RESTHandler))

    def test_hooks_called(self):
        # Verify hook is called when callback is executed
        self._config_change_called = False
        CoreHooks.attach("configuration_change", self._on_config_change)
        manager = ProjectManager()
        manager.trigger_config_change_hook('all')

        # handle async hook execution
        event = Event()
        condition = ConditionWaiter(event, self._verify_config_change_called)
        condition.start()
        self.assertTrue(event.wait(1))
        condition.stop()

    def _on_config_change(self, cfg_type):
        self._config_change_called = True

    def _verify_config_change_called(self):
        return self._config_change_called
