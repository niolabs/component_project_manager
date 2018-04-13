from os import path

from unittest.mock import ANY, patch, Mock
from niocore.core.context import CoreContext
from nio.modules.persistence import Persistence
from nio.modules.web import RESTHandler
from niocore.util.environment import NIOEnvironment
from niocore.testing.test_case import NIOCoreTestCase

from ..manager import ProjectManager


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

    def test_clone_on_configure(self):
        """ Test that blocks get cloned when the component configures """
        persistence = Persistence()
        blocks = {
            "blocks": [
                "block_1_as_str",
                {
                    "url": "block_2_as_dict",
                    "branch": "block_2_branch"
                },
                {
                    "url": "block_3_no_branch"
                }
            ]
        }
        persistence.save(blocks, "blocks")

        rest_manager = Mock()
        context = CoreContext([], [])
        project_manager = ProjectManager()
        project_manager.get_dependency = Mock(return_value=rest_manager)

        with patch.object(project_manager, 'clone_block') as clone_mock:
            project_manager.configure(context)
            # Make sure we got all 3 clone calls properly
            self.assertEqual(clone_mock.call_count, 3)

            # Block 1 only provided a string for the URL
            self.assertEqual(
                clone_mock.call_args_list[0][0][0],
                'block_1_as_str')
            self.assertIsNone(clone_mock.call_args_list[0][1]['branch'])

            # Block 2 provided both url and branch
            self.assertEqual(
                clone_mock.call_args_list[1][0][0],
                'block_2_as_dict')
            self.assertEqual(
                clone_mock.call_args_list[1][1]['branch'],
                'block_2_branch')

            # Block 3 only provided a string for the URL but inside a dict
            self.assertEqual(
                clone_mock.call_args_list[2][0][0],
                'block_3_no_branch')
            self.assertIsNone(clone_mock.call_args_list[2][1]['branch'])

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

    @patch(ProjectManager.__module__ + ".path.isdir")
    @patch(ProjectManager.__module__ + ".listdir")
    @patch(ProjectManager.__module__ + ".chdir")
    @patch(ProjectManager.__module__ + ".subprocess")
    def test_clone_block_to_existent_directory(
            self, subprocess_patch, chdir_patch, listdir_patch, isdir_patch):
        """ Asserts clone ops are skipped if dir exists and is not empty
        """

        project_manager = ProjectManager()
        project_manager.get_dependency = Mock()
        project_manager.configure(CoreContext([], []))

        listdir_patch.return_value = ['foo']
        isdir_patch.return_value = True
        url = "block_template"
        result = project_manager.clone_block(url, error_on_existing_repo=False)
        self.assertNotEqual(result["status"], "ok")
        self.assertFalse(subprocess_patch.call_count)
        # assert that previous directory was restored
        self.assertEqual(chdir_patch.call_count, 2)
        self.assertEqual(chdir_patch.call_args_list[-1][0][0],
                         self._root_path)
        with self.assertRaises(ValueError):
            project_manager.clone_block(url, error_on_existing_repo=True)
        # assert error_on_existing_repo default
        with self.assertRaises(ValueError):
            project_manager.clone_block(url)

    @patch(ProjectManager.__module__ + ".chdir")
    @patch(ProjectManager.__module__ + ".subprocess")
    def test_clone_blocks_ok(self, subprocess_patch, chdir_patch):
        """ Asserts different url specifications
        """

        subprocess_patch.call = Mock(return_value=0)

        project_manager = ProjectManager()
        project_manager.get_dependency = Mock()
        project_manager.configure(CoreContext([], []))

        # specify just block as url
        url = "block_template"
        result = project_manager.clone_block(url)
        self.assertEqual(result["status"], "ok")
        # assert that it used https
        cmd = "git clone --recursive " \
            "git://github.com/nio-blocks/block_template.git"
        subprocess_patch.call.assert_any_call(cmd, shell=True)
        subprocess_patch.call.reset_mock()

        # assert that chdir call happened
        self.assertGreaterEqual(chdir_patch.call_count, 1)
        first_chdir_call_arg, = chdir_patch.call_args_list[0][0]
        self.assertEqual(first_chdir_call_arg,
                         path.join(self._root_path, "blocks"))
        # assert that previous directory was restored
        second_chdir_call_arg, = chdir_patch.call_args_list[1][0]
        self.assertEqual(second_chdir_call_arg, self._root_path)

        # specify nio-blocks as part of the url
        url = "nio-blocks/block_template"
        result = project_manager.clone_block(url)
        self.assertEqual(result["status"], "ok")
        # assert cmd as expected
        cmd = "git clone --recursive " \
            "git://github.com/nio-blocks/block_template.git"

        self.assertEqual(result["status"], "ok")
        subprocess_patch.call.assert_any_call(cmd, shell=True)
        subprocess_patch.call.reset_mock()

        # specify full url
        url = "git@github.com:nio-blocks/block_template"
        result = project_manager.clone_block(url)
        self.assertEqual(result["status"], "ok")
        # assert that git url is as entered (no https this time)
        cmd = "git clone --recursive " \
              "git@github.com:nio-blocks/block_template.git"
        subprocess_patch.call.assert_any_call(cmd, shell=True)
        subprocess_patch.call.reset_mock()

        # another full url format
        url = "https://github.com/nio-blocks/util.git"
        result = project_manager.clone_block(url)
        self.assertEqual(result["status"], "ok")
        # assert that git url is as entered
        cmd = "git clone --recursive https://github.com/nio-blocks/util.git"
        subprocess_patch.call.assert_any_call(cmd, shell=True)
        subprocess_patch.call.reset_mock()

        # specify a tag
        url = "https://github.com/nio-blocks/util.git"
        result = project_manager.clone_block(url, tag="v1.0.1")
        self.assertEqual(result["status"], "ok")
        # assert that git url is as entered
        cmd = "git clone --recursive https://github.com/nio-blocks/util.git"
        subprocess_patch.call.assert_any_call(cmd, shell=True)
        cmd = "git checkout v1.0.1"
        subprocess_patch.call.assert_any_call(cmd, shell=True)
        subprocess_patch.call.reset_mock()

        # specify a branch
        url = "https://github.com/nio-blocks/util.git"
        result = project_manager.clone_block(url, tag="v1.0.1", branch="b1")
        self.assertEqual(result["status"], "ok")
        # assert that git url is as entered
        cmd = "git clone --recursive https://github.com/nio-blocks/util.git " \
              "-b b1"
        subprocess_patch.call.assert_any_call(cmd, shell=True)
        cmd = "git checkout v1.0.1"
        subprocess_patch.call.assert_any_call(cmd, shell=True)
        subprocess_patch.call.reset_mock()

    @patch(ProjectManager.__module__ + ".subprocess")
    def test_clone_blocks_not_ok(self, subprocess_patch):
        """ Asserts failure to clone when subprocess call fails
        """
        subprocess_patch.call = Mock(return_value=128)

        project_manager = ProjectManager()

        # save current directory and make sure it does not change after
        # a failed clone_block operation
        prev_directory = path.abspath(path.curdir)

        url = "block_template"
        # assert failure to clone
        with self.assertRaises(ValueError):
            project_manager.clone_block(url)

        cmd = "git clone --recursive " \
            "git://github.com/nio-blocks/block_template.git"
        # since this call fails, there is only one subprocess call
        subprocess_patch.call.assert_called_once_with(cmd, shell=True)
        subprocess_patch.call.reset_mock()

        self.assertEqual(prev_directory, path.abspath(path.curdir))

    def test_update_block_ok(self):

        project_manager = ProjectManager()
        project_manager._subprocess_call = Mock(return_value=0)

        # save current directory and make sure it does not change after
        # an update_block operation
        prev_directory = path.abspath(path.curdir)

        results = project_manager.update_block(["twitter"])
        self.assertIn("twitter", results[0])
        self.assertEqual(results[0]["twitter"]["status"], "ok")

        # assert fetch and update submodule calls
        self.assertEqual(project_manager._subprocess_call.call_count, 2)

        # assert fetch call arguments
        project_manager._subprocess_call.assert_any_call(
            "git fetch origin --progress --prune")

        self.assertEqual(prev_directory, path.abspath(path.curdir))

    def test_update_invalid_block(self):

        project_manager = ProjectManager()
        project_manager._subprocess_call = Mock(return_value=0)

        project_manager._subprocess_call.reset_mock()
        results = project_manager.update_block(["invalid_block"])
        self.assertEqual(len(results), 1)
        self.assertIn("not installed", results[0])
        self.assertEqual(len(results[0]["not installed"]), 1)
        self.assertEqual(results[0]["not installed"][0], "invalid_block")
        self.assertEqual(project_manager._subprocess_call.call_count, 0)

    def test_update_all(self):
        # asserts that when no blocks are specified, all installed blocks
        # are updated

        project_manager = ProjectManager()
        project_manager._subprocess_call = Mock(return_value=0)

        # save current directory and make sure it does not change after
        # an update_block operation
        prev_directory = path.abspath(path.curdir)

        results = project_manager.update_block([])

        # there are four entries, one for each block updated
        # and one entry for possible blocks called for an update
        # that were not even installed in the system
        self.assertEqual(len(results), 4)
        # assert that all blocks in project_path were updated
        self.assertIn({"twitter": {"status": "ok"}}, results)
        self.assertIn({"mongo": {"status": "ok"}}, results)
        self.assertIn({"dummy_block": {"status": "ok"}}, results)
        # assert 'not installed' blocks entry is empty (for a non-empty
        # 'not installed' entry see test_update_invalid_block
        self.assertIn({"not installed": []}, results)

        # assert fetch and update submodule calls
        self.assertEqual(project_manager._subprocess_call.call_count, 4)

        # assert fetch call arguments
        project_manager._subprocess_call.assert_any_call(
            "git fetch origin --progress --prune")

        self.assertEqual(prev_directory, path.abspath(path.curdir))
