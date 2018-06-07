"""

    Project Manager

"""
import subprocess
from os import listdir, path, remove, chdir, popen
from shutil import rmtree
from urllib.parse import urlparse, urlunparse
from copy import deepcopy

from nio.modules.persistence import Persistence
from nio.util.logging import get_nio_logger
from nio.util.versioning.dependency import DependsOn
from niocore.core.component import CoreComponent
from niocore.util.environment import NIOEnvironment
from nio import discoverable

from .handler import ProjectManagerHandler
from . import __version__ as component_version


@DependsOn("niocore.components.rest", "0.1.0")
@discoverable
class ProjectManager(CoreComponent):

    """ Core component to handle project management functionality

    """

    _name = "ProjectManager"

    exclusions = ["__pycache__",
                  ".git",
                  "__init__.py",
                  "README.md",
                  ".DS_Store"]

    def __init__(self):
        """Initializes the component

        """
        super().__init__()
        self._handler = None

        # dependency components
        self._rest_manager = None
        self._block_manager = None

        # allocate persistence instance to use to load/save cloned blocks
        self._persistence = Persistence()
        self._blocks_from = None

    def get_version(self):
        return component_version

    def configure(self, context):
        """ Configures project manager

        Makes sure it gets a reference to its dependencies

        Args:
            context (CoreContext): component initialization context

        """

        super().configure(context)

        # Register dependencies to rest and block manager
        self._rest_manager = self.get_dependency("RESTManager")
        self._block_manager = self.get_dependency("BlockManager")

        # Clone down any blocks that were configured in the instance settings
        try:
            self._clone_configured_blocks()
        # catch the two known exceptions that a corrupt/invalid file might throw
        except (TypeError, ValueError):
            # log and allow nio to continue
            self.logger.exception(
                "An error has occurred while making sure installed block source"
                " files are present, please verify that 'blocks.cfg' entries"
                " are valid")

    def start(self):
        """Starts component

        Creates and registers web handler

        """
        super().start()

        # create REST specific handlers
        self._handler = ProjectManagerHandler("/project", self)

        # Add handler to WebServer
        self._rest_manager.add_web_handler(self._handler)

    def stop(self):
        """Stops component

        Removes web handler

        """
        # Remove handler from WebServer
        self._rest_manager.remove_web_handler(self._handler)
        super().stop()

    def get_order(self):
        """ Get the order the component will start/configure in.

        We want to make sure that this component configures before
        the BlockManager since we will be cloning blocks and we want
        that component to be able to discover them.
        """
        return 30

    def _clone_configured_blocks(self):
        """ Clone down blocks that the instance needs

        If the instance config specifies blocks to clone in the settings
        then clone them down now, before the BlockManager does its
        discovery.
        """

        # load blocks to clone,
        # for file persistence, it will load from etc/blocks.cfg
        # for redis persistence, it will load from field 'blocks' and hash 'nio'
        self._blocks_from = self._persistence.load("blocks",
                                                   default={"blocks": []})

        if not self._blocks_from:
            self.logger.debug("No blocks to clone")

        # perform a deepcopy since clone_block might modify collection
        for block in deepcopy(self._blocks_from.get('blocks')):
            repo, tag, branch, path_to_block = self._parse_block(block)
            # Clone the repo with the configured branch. If the block already
            # exists in this project then it will NOT be overwritten and the
            # branch will not be switched
            try:
                self.clone_block(
                    repo, tag=tag, branch=branch, path_to_block=path_to_block,
                    error_on_existing_repo=False
                )
            except (TypeError, ValueError, RuntimeError):
                # log and allow cloning to continue
                self.logger.exception(
                    "An error has occurred while making sure installed block "
                    "source files are present, please verify that 'blocks.cfg' "
                    "entries are valid")

    def _parse_block(self, block):
        """ Parse a configured block into a URL and a branch

        This parse method allows the configuration to hold just the URL or a
        combination of a URL and branch. The configuration options are:

            {
                "url": "git@github.com:nio-blocks/filter.git",
                "tag": "v1.0.0",
                "branch": "master",
                "path": None
            }

            --- OR ---

            "git@github.com:nio-blocks/filter.git"

        Returns:
            repo_url, repo_branch: The URL and branch to checkout. If no
                branch is specified, repo_branch will be None
        """
        if isinstance(block, str):
            # They only provided the URL, don't return a branch
            return block, None, None, None

        if not isinstance(block, dict):
            raise TypeError("Block must be a string or dict")

        repo_url = block.get('url')
        tag = block.get('tag', None)
        repo_branch = block.get('branch', None)
        path_to_block = block.get('path', None)

        return repo_url, tag, repo_branch, path_to_block

    def get_blocks_structure(self, get_branch_info=False):
        """ Get block structure from disk

        Args:
            get_branch_info: Show git branches for each block

        Returns:
           Structure with an Array of blocks
        """

        # Return
        ret = []

        # Blocks from path
        blocks_paths = self._get_abs_blocks_paths()

        # Each block
        for blocks_path in blocks_paths:
            for item in listdir(blocks_path):

                # -- Discard known exclusions
                if item in ProjectManager.exclusions:
                    continue

                # -- Make block full path
                block_full_path = path.join(blocks_path, item)

                # -- Folder or file
                block = None
                if path.isdir(block_full_path):
                    block = {"name": item, "type": "directory"}
                elif path.isfile(block_full_path):
                    block = {"name": path.splitext(item)[0], "type": "file"}

                # -- Get branch info?
                if get_branch_info:
                    block["branch"] = self._get_git_branch(block_full_path)

                # -- Add block
                if block is not None:
                    ret.append(block)

        return {"blocks": ret}

    def _get_git_branch(self, directory):
        """Get Git branch

        Args:
            directory: path to block to get Git branch for


        Returns:
           String of branch name or None

        """

        # Command
        cmd = "cd %s && git rev-parse --abbrev-ref HEAD" % directory

        # Get git branch name
        result = popen(cmd).read().strip()

        # Result
        if len(result):
            return result

        return None

    def get_blocks(self, params):
        """Get blocks from params

        Consider url params to be block names, discard actual url param values

        Returns:
           Array of blocks

        """

        blocks = []
        for key, _ in params.items():
            blocks.extend([block.strip() for block in key.split(",")])

        return blocks

    def remove_blocks(self, blocks):
        """Remove blocks from disk

        Args:
            blocks: block folder

        Returns:
           Array of removed blocks

        """

        blocks_paths = self._get_abs_blocks_paths()
        removed = []
        for blocks_path in blocks_paths:
            for block in blocks:
                # create an absolute path and determine if it is valid
                block_full_path = path.join(blocks_path, block)
                if path.isdir(block_full_path):
                    self._remove_dir(block_full_path)
                    removed.append({"name": block,
                                    "type": "directory"})
                else:
                    # determine if it is a file
                    block_full_path_to_file = block_full_path + ".py"
                    if path.isfile(block_full_path_to_file):
                        self._remove_file(block_full_path_to_file)
                        removed.append({"name": block,
                                        "type": "file"})

        return removed

    def clone_block(self, url, tag=None, path_to_block=None, branch=None,
                    error_on_existing_repo=True):
        """Clones a block from github's nio-blocks repository

        Note: if a repository already exists at the given clone location
        then no clone will occur.

        Args:
            url: Where to get block from, following are valid
                /project/blocks url=https://github.com/nio-blocks/util.git
                /project/blocks url=git@github.com:nio-blocks/util.git
                /project/blocks url=util
                /project/blocks url=nio-blocks/util

            tag: tag to checkout (ignored if None)

            path_to_block: If None, path is figured out by accessing
                "blocks" entry from environment configuration

            branch: branch to clone (ignored if None)
            error_on_existing_repo (bool): if block is requested and it
                already exists

        Returns:
            Operation status as a dictionary
        """
        # save parameters that are modified so that we have a handle to them
        # if eventually need to be saved
        original_url = url
        original_path_to_block = path_to_block

        url = self._process_url(url)

        # Determine target path
        if not path_to_block:
            blocks_paths = self._get_abs_blocks_paths()
            if not blocks_paths:
                raise RuntimeError("Could not get a valid nio blocks path")
            # if no path specified, grab last path to blocks
            path_to_block = blocks_paths[len(blocks_paths)-1]

        # save directory to be restored
        directory_to_restore = path.abspath(path.curdir)
        try:
            chdir(path_to_block)
        except FileNotFoundError:
            msg = "Target block path '{0}' is invalid".format(path_to_block)
            self.logger.error(msg)
            raise ValueError(msg)

        # Get the directory that this will be cloned into
        block_dir, _ = path.splitext(path.basename(url))
        # check if relative path dir exists and if it is not empty
        if path.isdir(block_dir) and len(listdir(block_dir)):
            chdir(directory_to_restore)
            msg = "'{}' folder already exists and it is not empty, skipping".\
                  format(block_dir)
            if error_on_existing_repo:
                raise ValueError(msg)
            else:
                return {"status": msg}

        self.logger.info("Cloning Git repository into directory: {}"
                         .format(block_dir))
        res = self._clone_block_from_git(url, branch)
        result = self._get_subprocess_return(res, "cloning block")
        if result["status"] == "ok":
            # Update pip requirements
            self.pip_install_req("{0}/{1}".format(path_to_block, block_dir))

            if tag:
                self.logger.info("Checking out tag: {}".format(tag))

                # cd to folder and check out tag
                target_dir = path.join(path_to_block, block_dir)
                chdir(target_dir)
                res = self._subprocess_call("git checkout {}".format(tag))
                result = self._get_subprocess_return(res, "tag checkout")
                if result["status"] != "ok":
                    chdir(directory_to_restore)
                    self.logger.error(
                        "Failed to checkout specified tag: '{}'".
                        format(result["status"]))
                    # restoring original current directory
                    raise ValueError(result["status"])

            self.logger.info("Cloning block from: {0} was a success".
                             format(url))
            # validate block's modules
            valid, errors = \
                self._block_manager.validate_block_folder(block_dir)
            if not valid:
                # clean up/remove just downloaded block folder
                self._remove_dir(path.join(path_to_block, block_dir))

                chdir(directory_to_restore)
                raise RuntimeError(errors)

            # save it so that it is available next time if needed
            self._save_cloned_block(original_url,
                                    tag,
                                    branch,
                                    original_path_to_block)
        else:
            chdir(directory_to_restore)
            raise ValueError(result["status"])

        # restoring original current directory
        chdir(directory_to_restore)
        return result

    def _clone_block_from_git(self, url, branch=None):
        if branch is not None:
            self.logger.info(
                "Cloning {} branch for git repository: {}".format(branch, url))
            res = self._subprocess_call(
                "git clone --recursive {} -b {}".format(url, branch))
        else:
            self.logger.info(
                "Cloning default branch for git repository: {}".format(url))
            res = self._subprocess_call(
                "git clone --recursive {}".format(url))
        return res

    def pip_install_req(self, path_to_block):
        """Updates PIP requirements.txt file for a block

        Args:
            path_to_block: If None, path is figured out by accessing "blocks"
                entry from environment configuration

        Returns:
            Operation True or False
        """

        # Make path to requirements
        path_req = "{0}/requirements.txt".format(path_to_block)

        # Log
        self.logger.info("Install PIP requirements at {0}".format(path_req))

        # If we do not have a file, we are good
        if not path.isfile(path_req):
            return True

        try:
            # save directory to be restored
            directory_to_restore = path.abspath(path.curdir)
            # Change directory to block
            chdir(path_to_block)

        except FileNotFoundError:
            self.logger.error("Path '{0}' is invalid".format(path_to_block))
            raise

        # Pip install
        res = self._subprocess_call("pip3 install -r requirements.txt")
        # restoring original current directory
        chdir(directory_to_restore)
        if res != 0:
            return False

        return True

    def update_block(self, blocks):
        """Pulls down block latest version and updates submodules

        This method potentially updates all blocks in the system when incoming
        blocks parameter is an empty list.

        Additionally if 'blocks' list is not empty, and contains blocks that
        are not in the system, this method keeps track of such blocks and
        reports them as not installed.

        Args:
            blocks (list): blocks to update, if empty, all existing blocks are updated

        Returns:
            Operation status as a list with the following format:
            [
                {[block1]: {"status": [block1 update status]}},
                {[block2]: {"status": [block2 update status]]}},
                ...
                {[blockN]: {"status": [blockN update status]]}},
                {"not installed": [list of blocks requested but not installed}
            ]
        """

        results = []
        # keep a list of blocks requested but potentially not installed
        blocks_not_installed = deepcopy(blocks)

        # save directory to be restored
        directory_to_restore = path.abspath(path.curdir)

        blocks_paths = self._get_abs_blocks_paths()
        for blocks_path in blocks_paths:
            updates_in_path = False
            blocks_path_structure = self._get_block_path_structure(blocks_path)
            for block_structure in blocks_path_structure:
                if blocks:
                    if block_structure["name"] not in blocks:
                        # update was not requested for this block
                        continue
                    else:
                        # make sure block is counted as updated
                        blocks_not_installed.remove(block_structure["name"])

                if block_structure["type"] == "directory":
                    # cd to block directory
                    chdir(path.join(blocks_path, block_structure["name"]))
                else:
                    chdir(blocks_path)

                # update block
                result = self._get_subprocess_return(
                    self._subprocess_call(
                        "git fetch origin --progress --prune"),
                    "updating block")
                results.append({block_structure["name"]: result})
                updates_in_path = True

            # update submodules if there were any updates in path
            if updates_in_path:
                self._subprocess_call(
                    "git submodule update --init --recursive")

        # restoring original current directory
        chdir(directory_to_restore)

        if len(blocks_not_installed):
            # warning about requested blocks that were not found
            self.logger.warning("Blocks: {0} are not installed".
                                format(blocks_not_installed))
        results.append({"not installed": blocks_not_installed})

        return results

    @staticmethod
    def _get_subprocess_return(result, message):
        """Get subprocess results

        Args:
            result: Result from subprocess call
            message: Message to format result with

        Returns:
           Array with results of subprocess
        """

        if result < 0:
            result = {"status":
                      "while {0}, received killed by "
                      "signal: {1} status".format(message, result)}
        elif result > 0:
            result = {"status":
                      "while {0}, command failed with "
                      "return code: {1}".format(message, result)}
        else:
            # call is a success
            result = {"status": "ok"}

        return result

    @staticmethod
    def _get_abs_blocks_paths():
        """Get absolute path of blocks

        Returns:
           String with absolute path to blocks
        """

        blocks_resource_paths = NIOEnvironment.get_resource_paths('blocks',
                                                                  'blocks')
        abs_blocks_paths = []
        for blocks_resource_path in blocks_resource_paths:
            abs_block_path = NIOEnvironment.get_path(blocks_resource_path)
            if path.isdir(abs_block_path):
                abs_blocks_paths.append(abs_block_path)

        return abs_blocks_paths

    @staticmethod
    def _remove_dir(full_path):
        """Remove directory

        Args:
            full_path: Full path to directory

        Returns:
           True or false
        """

        try:

            # Sanity check
            if not path.isdir(full_path):
                return False

            # Delete directory
            rmtree(full_path)

        except Exception:

            # Log
            get_nio_logger("ProjectManager").exception(
                "Failure removing directory {0}".format(full_path))

            return False

        return True

    @staticmethod
    def _remove_file(file):
        """Remove file

        Args:
            file: Full path to file

        Returns:
           True or false
        """

        try:

            # Sanity check
            if not path.isfile(file):
                return False

            # Delete directory
            remove(file)

        except Exception:

            # Log
            get_nio_logger("ProjectManager").exception(
                "Failure removing file {0}".format(file))

            return False

        return True

    @staticmethod
    def _get_block_path_structure(blocks_path):
        """Return file structure under a given path

        Args:
            blocks_path: Path to blocks

        Returns:
            Array of blocks
        """

        blocks = []
        for item in listdir(blocks_path):
            # discard known exclusions
            if item in ProjectManager.exclusions:
                continue

            item_full_path = path.join(blocks_path, item)

            if path.isdir(item_full_path):
                blocks.append({"name": item,
                               "type": "directory"})
            elif path.isfile(item_full_path):
                blocks.append({"name": path.splitext(item)[0],
                               "type": "file"})

        return blocks

    @staticmethod
    def _subprocess_call(command):
        """Executes sub process command

        Returns:
           True or false
        """

        return subprocess.call(command, shell=True)

    @staticmethod
    def _subprocess_call_with_res(command):
        """Executes sub process command and returns response

        Returns:
           True or false
        """

        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
        res, err = process.communicate()

        return res

    def _save_cloned_block(self, url, tag, branch, path_to_block):
        """ Saves a clone operation parameters

        Overrides entry in case it existed so that latest parameters
        that gave origin to the block can be referenced

        Args:
            url: original block url (can be an incomplete url)
            tag: block tag
            branch: block branch
            path_to_block: block path
        """
        # find reference and remove it if it exists
        for block in self._blocks_from['blocks']:
            if isinstance(block, str):
                if url == block:
                    # save it now as dict
                    self._blocks_from['blocks'].remove(block)
                    break
            elif isinstance(block, dict):
                if block["url"] == url:
                    self._blocks_from['blocks'].remove(block)
                    break
        # add fresh entry
        self._blocks_from['blocks'].append(
            {
                "url": url,
                "tag": tag,
                "branch": branch,
                "path": path_to_block
            }
        )
        # persist it
        self._persistence.save(self._blocks_from, "blocks")

    @staticmethod
    def _process_url(url):
        """ Process given url filling in with 'nio defaults' when not complete

        This method 'decomposes' the url, check if the parts are complete, if
        not complete, it fills missing components with 'nio defaults' and
        composes it back

        Args:
            url (string): original url

        Returns:
            completed url
        """

        # <scheme>://<netloc>/<path>;<params>?<query>#<fragment>
        (scheme, netloc, path, params, query, fragment) = urlparse(url)
        if not path:
            raise ValueError("url must contain at least the block name")

        # remove ending '/' for simplicity
        if path.endswith("/"):
            path = path[:-1]
        if not path.endswith(".git"):
            path += ".git"

        # determine if path contains the 'org'
        # when a single string is provided it assumes 'block name'
        split_path = path.split('/')
        if len(split_path) == 2 and len(split_path[0]) == 0:
            # incoming path is a single string with '/' at the front
            path = "nio-blocks/{}".format(path[1:])
        elif len(split_path) == 1:
            # incoming path is a single string
            path = "nio-blocks/{}".format(path)

        # urlparse recognizes a netloc only if it is properly introduced
        # by ‘//’. Otherwise the input is presumed to be a relative URL
        # and thus to start with a path component
        if not netloc and not scheme and "@" not in path:
            if path.startswith('/'):
                path = path[1:]
            path = "git://github.com/{}".format(path)

        # put the url back together
        return urlunparse((scheme, netloc, path, params, query, fragment))
