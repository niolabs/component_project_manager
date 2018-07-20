from unittest.mock import MagicMock, patch
from nio.testing.modules.security.module import TestingSecurityModule
from nio.modules.web.http import Request, Response
from niocore.core.block.cloner import BlockCloner

from ..handler import ProjectManagerHandler
from niocore.testing.web_test_case import NIOCoreWebTestCase


class TestProjectManagerHandler(NIOCoreWebTestCase):

    def get_module(self, module_name):
        # Don't want to test permissions, use the test module
        if module_name == 'security':
            return TestingSecurityModule()
        else:
            return super().get_module(module_name)

    def test_on_get(self):
        project_manager = MagicMock()
        with patch.object(BlockCloner,
                          "get_blocks_structure") as get_struct_patch:
            get_struct_patch.return_value = {}
            handler = ProjectManagerHandler("", project_manager)

            request = MagicMock(spec=Request)
            request.get_params.return_value = {"identifier": "blocks"}
            response = MagicMock(spec=Response)
            handler.on_get(request, response)
            self.assertEqual(get_struct_patch.call_count, 1)

        # refresh request
        request = MagicMock(spec=Request)
        request.get_params.return_value = {"identifier": "refresh",
                                           "cfg_type": "block"}
        response = MagicMock(spec=Response)
        handler.on_get(request, response)
        self.assertEqual(
            project_manager.trigger_config_change_hook.call_count, 1)

        # invalid refresh request
        project_manager.reset_mock()
        request = MagicMock(spec=Request)
        request.get_params.return_value = {"identifier": "refresh",
                                           "cfg_type": "invalid"}
        response = MagicMock(spec=Response)
        with self.assertRaises(ValueError):
            handler.on_get(request, response)

        # invalid request
        mock_req = MagicMock(spec=Request)
        mock_req.get_params.return_value = {"identifier": "invalid"}
        handler = ProjectManagerHandler("", project_manager)

        # Verify error is raised with incorrect identifier
        request = mock_req
        response = MagicMock()
        with self.assertRaises(ValueError):
            handler.on_get(request, response)

    def test_on_get_invalid_params(self):
        handler = ProjectManagerHandler("", MagicMock())

        request = MagicMock(spec=Request)
        request.get_params.return_value = {"identifier": "invalid id"}
        response = MagicMock(spec=Response)
        with self.assertRaises(ValueError):
            handler.on_get(request, response)

    def test_on_delete(self):
        with patch.object(BlockCloner,
                          "remove_blocks") as remove_blocks_patch:
            remove_blocks_patch.return_value = {}

            handler = ProjectManagerHandler("", MagicMock())

            params = {"identifier": "blocks",
                      "twitter, filter": ""}
            request = MagicMock(spec=Request)
            request.get_params.return_value = params
            response = MagicMock(spec=Response)
            handler.on_delete(request, response)
            remove_blocks_patch.assert_called_with(
                ['twitter', 'filter'])

            remove_blocks_patch.reset_mock()
            params = {"identifier": "blocks",
                      "twitter": "",
                      "filter": ""}
            request = MagicMock(spec=Request)
            request.get_params.return_value = params
            response = MagicMock(spec=Response)
            handler.on_delete(request, response)
            # Don't know what order we will process the dictionary keys,
            # make sure both blocks were removed and nothing more
            call_args_removed = remove_blocks_patch.call_args[0][0]
            self.assertIn('twitter', call_args_removed)
            self.assertIn('filter', call_args_removed)
            self.assertEqual(len(call_args_removed), 2)

    def test_on_delete_invalid_params(self):
        with patch.object(BlockCloner,
                          "remove_blocks") as remove_blocks_patch:
            remove_blocks_patch.return_value = {}

            handler = ProjectManagerHandler("", MagicMock())

            params = {"identifier": "invalid_identifier",
                      "twitter, filter": ""}
            request = MagicMock(spec=Request)
            request.get_params.return_value = params
            response = MagicMock(spec=Response)
            with self.assertRaises(ValueError):
                handler.on_delete(request, response)
