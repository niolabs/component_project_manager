from os import path
from nio.util.logging import get_nio_logger
from .git import Git


class Blocks(object):
    """ A class containing helper functions to deal with installed blocks """

    blocks_dir = "blocks"
    logger = get_nio_logger('Project Manager')

    @staticmethod
    def get_block_url(block):
        """ Take a block string and return a full repository URL

        This method allows shorthand specifying of blocks in the nio-blocks
        repository. Mainly, it maps incomplete repository URLs into a full
        URL for the nio-blocks GitHub organization

        Returns:
            (str) A full repository URL that can be passed to git clone
                branch is specified, repo_branch will be None

        Raises:
            TypeError - block is not a string
        """
        if not isinstance(block, str):
            raise TypeError("Must specify block by a string")

        if not block.endswith(".git"):
            block = "{0}.git".format(block)

        # Assume nio-blocks repository if no repo name
        if "nio-blocks" not in block:
            block = "nio-blocks/{}".format(block)

        # Assume github.com for host
        if "github.com" not in block:
            block = "git@github.com:{}".format(block)

        return block

    @staticmethod
    def get_block_dir_from_repo(block_repo):
        """ For a given block repository, find the block directory it is in.

        This method will attempt to find an existing directory in the blocks
        directory that would represent the block specified by the block repo.
        Since all we provide as input is the block repository, we need this
        function to find an existing block to know if we need to clone a new
        one or just update an existing one.

        Args:
            block_repo (str): A string representing the block remote we are
                concerned with

        Returns:
            block_path (str): A string containing the relative path to the
                block. None if no path exists.
        """
        # Clean up the block repo name
        block_repo = Blocks.get_block_url(block_repo)
        # Find the ultimate directory the block would be cloned into by
        # taking the last directory item in the repository
        block_dir_name = block_repo.split('/')[-1].replace('.git', '')

        # Find the path relative to our block directory and return it if the
        # directory actually exists
        rel_block_path = path.join(Blocks.blocks_dir, block_dir_name)
        if path.exists(rel_block_path):
            Blocks.logger.debug(
                "Found existing block at {} for block repo {}".format(
                    rel_block_path, block_repo))
            return rel_block_path

        Blocks.logger.debug(
            "No existing blocks found for block repo {}".format(block_repo))
        return None

    @staticmethod
    def sync_block(block_repo, branch=None):
        """ Sync a block in the project with a repo and optionally branch

        This method will clone down a block repo if it doesn't already exist.
        If the block does it exist, it will update it to the latest version.
        If a branch is specified, the local repo will check out that branch.

        Args:
            block_repo (str): A string representing the block you wish to sync
            branch (str): An optional branch name to checkout

        Returns:
            None
        """
        block_path = Blocks.get_block_dir_from_repo(block_repo)

        if block_path is None:
            # The block doesn't exist, let's clone it
            Blocks.logger.debug(
                "Cloning a new block into {}".format(Blocks.blocks_dir))
            Git.clone_repo(
                Blocks.get_block_url(block_repo),
                Blocks.blocks_dir,
                branch=branch,
                shallow=True)
        else:
            # The block already exists, let's update it to this branch
            if branch is not None:
                # They specified a branch explicitly, let's check it out
                Blocks.logger.debug(
                    "Checking out branch {} for existing block repo {}".format(
                        branch, block_path))
                Git.checkout_latest_branch(block_path, branch)
            else:
                # No branch specified
                Blocks.logger.debug(
                    "Pulling changes for existing block repo {}".format(
                        block_path))
                Git.pull_latest(block_path)
