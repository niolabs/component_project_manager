from os import path
from unittest.mock import patch
from niocore.testing.test_case import NIOCoreTestCase
from ..git import Git
from ..blocks import Blocks


class TestBlocks(NIOCoreTestCase):

    def setUp(self):
        super().setUp()
        # For these tests our blocks directory is inside the project path
        self.orig_blocks_dir = Blocks.blocks_dir
        Blocks.blocks_dir = path.join(
            path.dirname(__file__), 'project_path/blocks')

    def tearDown(self):
        Blocks.blocks_dir = self.orig_blocks_dir
        super().tearDown()

    def test_block_url_formats(self):
        """ Make sure we accurately convert/format block repository URLs """
        # Should be able to specify just the block name, then assume SSH
        # and nio-blocks organization
        self.assertEqual(
            Blocks.get_block_url('test_block'),
            'git@github.com:nio-blocks/test_block.git')
        # Should be able to specify organization and block name, assume SSH
        self.assertEqual(
            Blocks.get_block_url('nio-blocks/test_block'),
            'git@github.com:nio-blocks/test_block.git')
        # Including the .git suffix is ok too
        self.assertEqual(
            Blocks.get_block_url('test_block.git'),
            'git@github.com:nio-blocks/test_block.git')
        # They should be able to specify a different GitHub organization
        # TODO: Make this test pass, current check for nio-blocks is bad
        # self.assertEqual(
            # Blocks.get_block_url('diff-org/test_block'),
            # 'git@github.com:diff-org/test_block.git')

        # If they want to use https then that's ok too
        self.assertEqual(
            Blocks.get_block_url('https://github.com/nio-blocks/test_block'),
            'https://github.com/nio-blocks/test_block.git')

        # Make sure our block URL is a string
        with self.assertRaises(TypeError):
            Blocks.get_block_url({'bad': 'block format'})

    def test_existing_block_dirs(self):
        """ Make sure we find existing folders that contain blocks """
        # Make sure we find our two existing blocks
        # For one, just give the block name. For the other, give a full repo
        self.assertIsNotNone(Blocks.get_block_dir_from_repo('mongo'))
        self.assertIsNotNone(Blocks.get_block_dir_from_repo(
            'git@github.com:nio-blocks/twitter.git'))

        # But don't find blocks that aren't installed yet
        self.assertIsNone(Blocks.get_block_dir_from_repo('not_a_block'))

    def test_sync(self):
        """ Test that we accurately sync blocks """
        blocks_dir = path.join(path.dirname(__file__), 'project_path/blocks')
        with patch("{}.Git".format(Blocks.__module__), spec=Git) as mock_git:
            # Try and sync an existing block to a new branch. This should
            # result in a git checkout
            Blocks.sync_block('mongo', 'new_branch')
            mock_git.checkout_latest_branch.assert_called_once_with(
                path.join(blocks_dir, 'mongo'),
                'new_branch')
            mock_git.reset_mock()

            # Try and sync an existing block without specifying a branch.
            # This one should just pull down the latest block
            Blocks.sync_block('twitter')
            mock_git.pull_latest.assert_called_once_with(
                path.join(blocks_dir, 'twitter'))
            mock_git.reset_mock()

            # A new block with a branch should call clone including the branch
            Blocks.sync_block('new_block_1', 'with_branch')
            mock_git.clone_repo.assert_called_once_with(
                'git@github.com:nio-blocks/new_block_1.git',
                blocks_dir,
                branch='with_branch',
                shallow=True)
            mock_git.reset_mock()

            # A new block without a branch should just call clone
            Blocks.sync_block('new_block_2')
            mock_git.clone_repo.assert_called_once_with(
                'git@github.com:nio-blocks/new_block_2.git',
                blocks_dir,
                branch=None,
                shallow=True)
            mock_git.reset_mock()
