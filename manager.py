"""

    Project Manager

"""
from nio.modules.persistence import Persistence
from nio.util.versioning.dependency import DependsOn
from niocore.core.component import CoreComponent
from niocore.core.block.cloner import BlockCloner
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
        self._block_cloner = None

        # allocate persistence instance to use to load/save cloned blocks
        self._persistence = Persistence()

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
        self._block_cloner = BlockCloner(self.get_dependency("BlockManager"))

    def start(self):
        """Starts component

        Creates and registers web handler

        """
        super().start()

        # create REST specific handlers
        self._handler = ProjectManagerHandler("/project",
                                              self._block_cloner)

        # Add handler to WebServer
        self._rest_manager.add_web_handler(self._handler)

    def stop(self):
        """Stops component

        Removes web handler

        """
        # Remove handler from WebServer
        self._rest_manager.remove_web_handler(self._handler)
        super().stop()
