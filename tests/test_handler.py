import threading
from unittest.mock import Mock
from nio.modules.security.user import User
from nio.modules.web.http import Request
from niocore.testing.test_case import NIOCoreTestCase

from ..handler import ProjectManagerHandler
from ..manager import ProjectManager


class TestProjectManagerHandler(NIOCoreTestCase):

    def get_test_modules(self):
        return super().get_test_modules() | {'security'}

    def setUp(self):
        super().setUp()
        setattr(threading.current_thread(), "user", User("tester"))

    def tearDown(self):
        delattr(threading.current_thread(), "user")
        super().tearDown()

    def _disable_security(self, handler):
        handler.commands = []

    def test_on_get(self):
        project_manager = ProjectManager()
        project_manager.get_blocks_structure = Mock(return_value={})
        handler = ProjectManagerHandler("", project_manager)
        self._disable_security(handler)

        params = {"identifier": "blocks"}
        request = Request(None, params, None)
        response = Mock()
        handler.on_get(request, response)
        project_manager.get_blocks_structure.assert_called_with()

    def test_on_get_invalid_params(self):
        project_manager = ProjectManager()
        handler = ProjectManagerHandler("", project_manager)
        self._disable_security(handler)

        params = {"identifier": "invalid_identifier"}
        request = Request(None, params, None)
        response = Mock()
        with self.assertRaises(ValueError):
            handler.on_get(request, response)

    def test_on_delete(self):
        project_manager = ProjectManager()
        project_manager.remove_blocks = Mock(return_value={})
        handler = ProjectManagerHandler("", project_manager)
        self._disable_security(handler)

        params = {"identifier": "blocks",
                  "twitter, filter": ""}
        request = Request(None, params, None)
        response = Mock()
        handler.on_delete(request, response)
        project_manager.remove_blocks.assert_called_with(
            ['twitter', 'filter'])

        project_manager.remove_blocks.reset_mock()
        params = {"identifier": "blocks",
                  "twitter": "",
                  "filter": ""}
        request = Request(None, params, None)
        response = Mock()
        handler.on_delete(request, response)
        # work around dict keys unpredictability
        args_ok = False
        try:
            project_manager.remove_blocks.assert_called_with(['twitter',
                                                              'filter'])
            args_ok = True
        except:
            pass
        try:
            project_manager.remove_blocks.assert_called_with(['filter',
                                                              'twitter'])
            args_ok = True
        except:
            pass
        self.assertTrue(args_ok)

    def test_on_delete_invalid_params(self):
        project_manager = ProjectManager()
        project_manager.remove_blocks = Mock(return_value={})
        handler = ProjectManagerHandler("", project_manager)
        self._disable_security(handler)

        params = {"identifier": "invalid_identifier",
                  "twitter, filter": ""}
        request = Request(None, params, None)
        response = Mock()
        with self.assertRaises(ValueError):
            handler.on_delete(request, response)
