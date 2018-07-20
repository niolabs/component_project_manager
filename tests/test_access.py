from unittest.mock import patch, Mock

from nio.modules.security import Authorizer, Unauthorized
from nio.modules.web.http import Request, Response
from nio.testing.test_case import NIOTestCase

from ..handler import ProjectManagerHandler


class TestAccess(NIOTestCase):

    def test_access(self):
        """ Asserts that API handlers are protected.
        """

        handler = ProjectManagerHandler("", None)
        with patch.object(Authorizer, "authorize",
                          side_effect=Unauthorized) as patched_authorize:

            with self.assertRaises(Unauthorized):
                request = Mock(spec=Request)
                request.get_params.return_value = {"identifier": "blocks"}
                handler.on_get(request, Mock(spec=Response))
            self.assertEqual(patched_authorize.call_count, 1)

            with self.assertRaises(Unauthorized):
                request = Mock(spec=Request)
                request.get_params.return_value = {"identifier": "refresh"}
                handler.on_get(request, Mock(spec=Response))
            self.assertEqual(patched_authorize.call_count, 2)

            with self.assertRaises(Unauthorized):
                handler.on_post(Mock(spec=Request), Mock(spec=Response))
            self.assertEqual(patched_authorize.call_count, 3)

            with self.assertRaises(Unauthorized):
                handler.on_put(Mock(spec=Request), Mock(spec=Response))
            self.assertEqual(patched_authorize.call_count, 4)

            with self.assertRaises(Unauthorized):
                handler.on_delete(Mock(spec=Request), Mock(spec=Response))
            self.assertEqual(patched_authorize.call_count, 5)
