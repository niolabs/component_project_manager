
from unittest.mock import patch, Mock
from nio.modules.persistence import Persistence
from niocore.testing.test_case import NIOCoreTestCase

from ..manager import ProjectManager


class TestProjectManager(NIOCoreTestCase):

    @patch(ProjectManager.__module__ + ".chdir")
    @patch(ProjectManager.__module__ + ".subprocess")
    def test_clone_blocks(self, subprocess_patch, chdir_patch):
        """ Asserts upon configuration configured blocks are cloned
        """
        def get_dependency(component):
            if component == "BlockManager":
                block_manager = Mock()
                # allow block_folder to validate fine
                block_manager.validate_block_folder.return_value = (True, {})
                return block_manager
            return Mock()

        blocks_count = 10
        blocks = []
        for i in range(blocks_count):
            blocks.append({"url": "block_{}".format(i)})

        Persistence().save({"blocks": blocks}, 'blocks')

        # make subprocess calls succeed so that clone block succeed for each
        subprocess_patch.call = Mock(return_value=0)

        project_manager = ProjectManager()
        self._orig_clone_block = project_manager.clone_block
        project_manager.clone_block = self._my_clone_block
        project_manager._get_abs_blocks_paths = Mock()
        project_manager._get_abs_blocks_paths.return_value = ["path1"]

        self._cloned_blocks = []
        project_manager.get_dependency = get_dependency
        project_manager.configure(Mock())

        # reload blocks and assert that the list kept the count
        blocks_loaded = Persistence().load("blocks")
        self.assertEqual(len(blocks_loaded["blocks"]), blocks_count)
        self.assertEqual(len(self._cloned_blocks), blocks_count)

        # assert that each block was cloned with expected url
        for i in range(blocks_count):
            block_found = False
            for cloned_block in self._cloned_blocks:
                if cloned_block == "block_{}".format(i):
                    block_found = True
                    break
            self.assertTrue(block_found)

    @patch(ProjectManager.__module__ + ".rmtree")
    @patch(ProjectManager.__module__ + ".chdir")
    @patch(ProjectManager.__module__ + ".subprocess")
    def test_clone_blocks_failing(self, subprocess_patch, chdir_patch,
                                  rmtree_patch):
        """ Asserts that failure to configure blocks is handled

        Even though blocks don't clone, configure call is allowed to continue
        """
        def get_dependency(component):
            if component == "BlockManager":
                block_manager = Mock()
                # allow block_folder to validate fine
                block_manager.validate_block_folder.return_value = (False, {})
                return block_manager
            return Mock()

        blocks_count = 10
        blocks = []
        for i in range(blocks_count):
            blocks.append({"url": "block_{}".format(i)})

        Persistence().save({"blocks": blocks}, 'blocks')

        # make subprocess calls succeed so that clone block succeed for each
        subprocess_patch.call = Mock(return_value=0)

        project_manager = ProjectManager()
        self._orig_clone_block = project_manager.clone_block
        project_manager.clone_block = self._my_clone_block
        project_manager._get_abs_blocks_paths = Mock()
        project_manager._get_abs_blocks_paths.return_value = ["path1"]

        self._cloned_blocks = []
        project_manager.get_dependency = get_dependency
        project_manager.configure(Mock())

        self.assertEqual(len(self._cloned_blocks), 0)

    def _my_clone_block(self, url, tag=None, path_to_block=None, branch=None,
                        error_on_existing_repo=True):
        self._orig_clone_block(url, tag, path_to_block, branch,
                               error_on_existing_repo)
        self._cloned_blocks.append(url)
