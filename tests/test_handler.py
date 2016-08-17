from unittest.mock import MagicMock
from nio.testing.modules.security.module import TestingSecurityModule
from nio.modules.web.http import Request, Response

from ..handler import ProjectManagerHandler
from ..manager import ProjectManager
from niocore.testing.web_test_case import NIOCoreWebTestCase


class TestProjectManagerHandler(NIOCoreWebTestCase):

    def get_module(self, module_name):
        # Don't want to test permissions, use the test module
        if module_name == 'security':
            return TestingSecurityModule()
        else:
            return super().get_module(module_name)

    def test_on_get(self):
        project_manager = ProjectManager()
        project_manager.get_blocks_structure = MagicMock(return_value={})
        handler = ProjectManagerHandler("", project_manager)

        request = MagicMock(spec=Request)
        request.get_params.return_value = {"identifier": "blocks"}
        response = MagicMock(spec=Response)
        handler.on_get(request, response)
        self.assertEqual(project_manager.get_blocks_structure.call_count, 1)

    def test_on_get_invalid_params(self):
        project_manager = ProjectManager()
        handler = ProjectManagerHandler("", project_manager)

        request = MagicMock(spec=Request)
        request.get_params.return_value = {"identifier": "invalid id"}
        response = MagicMock(spec=Response)
        with self.assertRaises(ValueError):
            handler.on_get(request, response)

    def test_on_delete(self):
        project_manager = ProjectManager()
        project_manager.remove_blocks = MagicMock(return_value={})
        handler = ProjectManagerHandler("", project_manager)

        params = {"identifier": "blocks",
                  "twitter, filter": ""}
        request = MagicMock(spec=Request)
        request.get_params.return_value = params
        response = MagicMock(spec=Response)
        handler.on_delete(request, response)
        project_manager.remove_blocks.assert_called_with(
            ['twitter', 'filter'])

        project_manager.remove_blocks.reset_mock()
        params = {"identifier": "blocks",
                  "twitter": "",
                  "filter": ""}
        request = MagicMock(spec=Request)
        request.get_params.return_value = params
        response = MagicMock(spec=Response)
        handler.on_delete(request, response)
        # Don't know what order we will process the dictionary keys,
        # make sure both blocks were removed and nothing more
        call_args_removed = project_manager.remove_blocks.call_args[0][0]
        self.assertIn('twitter', call_args_removed)
        self.assertIn('filter', call_args_removed)
        self.assertEqual(len(call_args_removed), 2)

    def test_on_delete_invalid_params(self):
        project_manager = ProjectManager()
        project_manager.remove_blocks = MagicMock(return_value={})
        handler = ProjectManagerHandler("", project_manager)

        params = {"identifier": "invalid_identifier",
                  "twitter, filter": ""}
        request = MagicMock(spec=Request)
        request.get_params.return_value = params
        response = MagicMock(spec=Response)
        with self.assertRaises(ValueError):
            handler.on_delete(request, response)
