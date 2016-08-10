from os import path, chdir

from unittest.mock import ANY, patch, Mock
from niocore.core.context import CoreContext
from nio.modules.web import RESTHandler
from niocore.util.environment import NIOEnvironment
from niocore.testing.test_case import NIOCoreTestCase

from ..manager import ProjectManager


class TestProjectManager(NIOCoreTestCase):

    def setUp(self):

        self._saved_dir = path.abspath(path.curdir)

        # save previous environment
        self._saved_root = NIOEnvironment._root
        self._saved_conf_file = NIOEnvironment._conf_file
        self._saved_env_file = NIOEnvironment._env_file
        self._saved_env_vars = NIOEnvironment._env_vars

        # override NIO environment before Settings module is initialized
        self._root_path = path.join(
            path.dirname(path.abspath(path.realpath(__file__))),
            'project_path')
        NIOEnvironment.set_environment(self._root_path, 'nio.conf', 'nio.env')

        super().setUp()

    def tearDown(self):

        # restore previous environment
        NIOEnvironment._root = self._saved_root
        NIOEnvironment._conf_file = self._saved_conf_file
        NIOEnvironment._env_file = self._saved_env_file
        NIOEnvironment._env_vars = self._saved_env_vars

        # restore original current directory
        chdir(self._saved_dir)

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

    def test_get_blocks_structure(self):
        # asserts that blocks retrieved match defined structure

        project_manager = ProjectManager()
        blocks_structure = project_manager.get_blocks_structure(0)
        # test against defined structure
        items_to_find = [("mongo", "directory"),
                         ("twitter", "directory"),
                         ("dummy_block", "file")]

        # assert that same number of items was found
        self.assertEqual(len(items_to_find), len(blocks_structure["blocks"]))

        # assert that each one has a match
        for item_to_find in items_to_find:
            found = False
            name, _type = item_to_find
            for item in blocks_structure["blocks"]:
                if item["name"] == name and item["type"] == _type:
                    found = True
                    break
            self.assertTrue(found)

    def test_remove_blocks(self):
        # asserts that blocks retrieved match defined structure

        project_manager = ProjectManager()

        # mock actual remove methods
        project_manager._remove_dir = Mock()
        project_manager._remove_file = Mock()

        project_manager.remove_blocks(["dummy_block", "mongo"])

        root_path = path.join(
            path.dirname(path.abspath(path.realpath(__file__))),
            'project_path')
        path_to_mongo = path.join(root_path, "blocks", "mongo")
        project_manager._remove_dir.assert_called_with(path_to_mongo)

        path_to_dummy_block = path.join(root_path, "blocks", "dummy_block.py")
        project_manager._remove_file.assert_called_with(path_to_dummy_block)

    @patch(ProjectManager.__module__ + ".chdir")
    @patch(ProjectManager.__module__ + ".subprocess")
    def test_clone_blocks_ok(self, subprocess_patch, chdir_patch):

        subprocess_patch.call = Mock(return_value=0)

        project_manager = ProjectManager()
        url = "block_template"
        result = project_manager.clone_block(url, None)

        self.assertEqual(result["status"], "ok")
        # two subprocess calls, first to clone, second to update submodules

        cmd = "git clone --recursive " \
              "git@github.com:nio-blocks/block_template.git"
        subprocess_patch.call.assert_any_call(cmd, shell=True)
        subprocess_patch.call.reset_mock()

        # assert that chdir call happened
        chdir_patch.assert_called_once_with(path.join(self._root_path,
                                                      "blocks"))

        url = "nio-blocks/block_template"
        result = project_manager.clone_block(url, None)

        cmd = "git clone --recursive " \
              "git@github.com:nio-blocks/block_template.git"

        self.assertEqual(result["status"], "ok")
        subprocess_patch.call.assert_any_call(cmd, shell=True)
        subprocess_patch.call.reset_mock()

        # full url
        url = "git@github.com:nio-blocks/block_template"
        result = project_manager.clone_block(url, None)

        cmd = "git clone --recursive " \
              "git@github.com:nio-blocks/block_template.git"

        self.assertEqual(result["status"], "ok")
        subprocess_patch.call.assert_any_call(cmd, shell=True)
        subprocess_patch.call.reset_mock()

        # another full url format
        url = "https://github.com/nio-blocks/util.git"
        result = project_manager.clone_block(url, None)

        cmd = "git clone --recursive https://github.com/nio-blocks/util.git"

        self.assertEqual(result["status"], "ok")
        subprocess_patch.call.assert_any_call(cmd, shell=True)
        subprocess_patch.call.reset_mock()

    @patch(ProjectManager.__module__ + ".subprocess")
    def test_clone_blocks_not_ok(self, subprocess_patch):

        subprocess_patch.call = Mock(return_value=128)

        project_manager = ProjectManager()

        url = "block_template"
        result = project_manager.clone_block(url, None)
        self.assertNotEqual(result["status"], "ok")

        cmd = "git clone --recursive " \
              "git@github.com:nio-blocks/block_template.git"

        # since this call fails, there is only one subprocess call
        subprocess_patch.call.assert_called_once_with(cmd, shell=True)
        subprocess_patch.call.reset_mock()

    def test_update_block_ok(self):

        project_manager = ProjectManager()
        project_manager._subprocess_call = Mock(return_value=0)

        results = project_manager.update_block(["twitter"])
        self.assertIn("twitter", results[0])
        self.assertEqual(results[0]["twitter"]["status"], "ok")

        # assert fetch and update submodule calls
        self.assertEqual(project_manager._subprocess_call.call_count, 2)

        # assert fetch call arguments
        project_manager._subprocess_call.assert_any_call(
            "git fetch origin --progress --prune")


    def test_update_invalid_block(self):

        project_manager = ProjectManager()
        project_manager._subprocess_call = Mock(return_value=0)

        project_manager._subprocess_call.reset_mock()
        results = project_manager.update_block(["invalid_block"])
        self.assertEqual(len(results), 0)
        self.assertEqual(project_manager._subprocess_call.call_count, 0)

    def test_update_all(self):
        # asserts that when no blocks are specified, all installed blocks
        # are updated

        project_manager = ProjectManager()
        project_manager._subprocess_call = Mock(return_value=0)

        results = project_manager.update_block([])

        # assert that all blocks in project_path were updated
        self.assertEqual(len(results), 3)
        self.assertIn({"twitter": {"status": "ok"}}, results)
        self.assertIn({"mongo": {"status": "ok"}}, results)
        self.assertIn({"dummy_block": {"status": "ok"}}, results)

        # assert fetch and update submodule calls
        self.assertEqual(project_manager._subprocess_call.call_count, 4)

        # assert fetch call arguments
        project_manager._subprocess_call.assert_any_call(
            "git fetch origin --progress --prune")
