from nio.testing.test_case import NIOTestCase

from ..manager import ProjectManager


class TestProcessUrl(NIOTestCase):

    def test_process_url(self):
        urls = [
            (
                "ssh://git@gitlab.org.net:12345/org/repo.git",
                "ssh://git@gitlab.org.net:12345/org/repo.git"),
            (
                "git://git@github.com:12345/org/repo.git",
                "git://git@github.com:12345/org/repo.git"
            ),
            (
                "git://host.xz/path/to/repo.git/",
                "git://host.xz/path/to/repo.git"
             ),
            (
                "http://host.xz/path/to/repo.git/",
                "http://host.xz/path/to/repo.git"
            ),
            (
                "nio-blocks/simulator",
                "git://github.com/nio-blocks/simulator.git"
            ),
            (
                "own_org/simulator",
                "git://github.com/own_org/simulator.git"
            ),
            (
                "/own_org/simulator",
                "git://github.com/own_org/simulator.git"
            ),
            (
                "/simulator",
                "git://github.com/nio-blocks/simulator.git"
            ),
            (
                "simulator",
                "git://github.com/nio-blocks/simulator.git"
            ),
            (
                "git@github.com:nio-blocks/block_template.git",
                "git@github.com:nio-blocks/block_template.git"
            ),
            (
                "https://git@github.com/nio-blocks/block_template.git",
                "https://git@github.com/nio-blocks/block_template.git"
            )
        ]
        pm = ProjectManager()
        for (raw_url, expected_url) in urls:
            self.assertEqual(pm._process_url(raw_url), expected_url)
