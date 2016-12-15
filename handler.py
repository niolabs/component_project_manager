"""

    Project Manager Handler

"""
import json
from nio.modules.security.access import ensure_access
from nio.util.logging import get_nio_logger
from nio.modules.web import RESTHandler


class ProjectManagerHandler(RESTHandler):
    """ Handles 'project' API requests
    """

    def __init__(self, route, project_manager):
        super().__init__(route)
        self._project_manager = project_manager
        self.logger = get_nio_logger("ProjectManagerHandler")

    def on_get(self, request, response, *args, **kwargs):
        """ API endpoint to retrieve current block structure

        Example:
            http://[host]:[port]/project/blocks
            http://[host]:[port]/project/blocks?branches=1

        """

        # Ensure instance "read" access in order to retrieve project blocks
        # structure
        ensure_access("instance", "read")

        # Log
        params = request.get_params()
        self.logger.debug("on_get, params: {0}".format(params))

        # Result default to none
        result = None

        # What route?
        if "identifier" in params:

            # -- Blocks
            if params["identifier"] == "blocks":

                # -- Get branch info
                get_branch_info = bool(params.get("branches", 0))

                # -- -- Get block structure
                result = \
                    self._project_manager.get_blocks_structure(get_branch_info)

        # Result
        if result is not None:
            response.set_header('Content-Type', 'application/json')
            response.set_body(json.dumps(result))
        else:
            raise ValueError("GET request with params: {0} is invalid".
                             format(params))

    def on_delete(self, request, response):
        """ API endpoint to handle 'delete' block from repository

        Example:
            delete: http://[host]:[port]/project/blocks?util

        """
        # Ensure instance "write" access in order to delete blocks from
        # repository
        ensure_access("instance", "write")

        params = request.get_params()
        self.logger.debug("on_delete, params: {0}".format(params))

        result = None
        if "identifier" in params:
            if params["identifier"] == "blocks":
                del params["identifier"]
                # consider url params to be block names,
                # discard actual url param values
                blocks = self._project_manager.get_blocks(params)
                if blocks:
                    result = self._project_manager.remove_blocks(blocks)

        if result is not None:
            response.set_header('Content-Type', 'application/json')
            response.set_body(json.dumps(result))
        else:
            raise ValueError("DELETE request with params: {0} is invalid".
                             format(params))

    def on_post(self, request, response, *args, **kwargs):
        """ API endpoint to handle 'clone' and/or 'update' repository operations

        Example:
            clone:
             http://[host]:[port]/project/blocks with body: {"url": [block]}
            update:
             http://[host]:[port]/project/blocks?[block1],[block2],...,[blockN]

        """
        # Ensure instance "write" access in order to modify blocks repository
        ensure_access("instance", "write")

        params = request.get_params()
        body = request.get_body()
        self.logger.debug("on_post, params: {0}, body: {1}".
                          format(params, body))

        result = None
        msg = ""
        if "identifier" in params:
            if params["identifier"] == "blocks":
                if "url" in body:
                    # access url
                    url = body["url"]
                    # target path, if no path available, system will provide it
                    path_to_block = body["path"] if "path" in body else None

                    result = \
                        self._project_manager.clone_block(url, path_to_block)
                else:
                    # when no url is specified, then default to blocks,
                    # in which case, interpret it as block updates
                    # []/project/blocks?twitter&util or
                    # []/project/blocks?twitter,util
                    del params["identifier"]
                    blocks = self._project_manager.get_blocks(params)
                    result = self._project_manager.update_block(blocks)

        if result is not None:
            response.set_header('Content-Type', 'application/json')
            response.set_body(json.dumps(result))
        else:
            raise ValueError("POST/PUT request with params: {0} and body: {1} "
                             "is invalid {2}".format(params, body, msg))

    def on_put(self, request, response, *args, **kwargs):
        """ API endpoint to handle 'clone' and/or 'update' repository operations

            Passes along to on_post handler.
        """

        return self.on_post(request, response, args, kwargs)
