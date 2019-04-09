# Copyright (c) 2019-present, Facebook, Inc.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import unittest
from typing import Iterable
from unittest.mock import call, patch

from .. import filesystem
from ..build_target import Glob, Sources
from ..filesystem import resolve_sources


class FilesystemTest(unittest.TestCase):
    def assert_paths_match(self, first: Iterable[str], second: Iterable[str]) -> None:
        self.assertListEqual(sorted(first), sorted(second))

    @patch.object(filesystem, "get_filesystem")
    def test_resolve_sources(self, mock_filesystem):
        mock_list = mock_filesystem.return_value.list
        directory = "/project"

        sources = resolve_sources(directory, Sources(files=["a.py", "b.py"]))
        self.assert_paths_match(sources, ["/project/a.py", "/project/b.py"])

        # Duplicates are filtered out.
        sources = resolve_sources(directory, Sources(files=["a.py", "b.py", "a.py"]))
        self.assert_paths_match(sources, ["/project/a.py", "/project/b.py"])

        mock_list.return_value = ["dir/c.py", "dir/d.py"]
        sources = resolve_sources(directory, Sources(globs=[Glob(["dir/*.py"], [])]))
        self.assert_paths_match(sources, ["/project/dir/c.py", "/project/dir/d.py"])
        mock_list.assert_called_once_with("/project", ["dir/*.py"], exclude=[])
        mock_list.reset_mock()

        mock_list.return_value = [
            "/project/dir/c.py",
            "/project/dir/d.py",
            "/project/other_dir/g.py",
        ]
        sources = resolve_sources(
            directory, Sources(globs=[Glob(["dir/*.py", "other_dir/*.py"], [])])
        )
        self.assert_paths_match(
            sources,
            ["/project/dir/c.py", "/project/dir/d.py", "/project/other_dir/g.py"],
        )
        mock_list.assert_called_once_with(
            "/project", ["dir/*.py", "other_dir/*.py"], exclude=[]
        )
        mock_list.reset_mock()

        mock_list.return_value = ["dir/foo/e.py", "dir/foo/f.py", "other_dir/g.py"]
        sources = resolve_sources(
            directory,
            Sources(globs=[Glob(["dir/**/*.py", "other_dir/*.py"], ["dir/*.py"])]),
        )
        self.assert_paths_match(
            sources,
            [
                "/project/dir/foo/e.py",
                "/project/dir/foo/f.py",
                "/project/other_dir/g.py",
            ],
        )
        mock_list.assert_called_once_with(
            "/project", ["dir/**/*.py", "other_dir/*.py"], exclude=["dir/*.py"]
        )
        mock_list.reset_mock()

        # Excludes only apply to the glob they're used in.
        mock_list.side_effect = [
            ["dir/foo/e.py", "dir/foo/f.py", "other_dir/g.py"],
            ["dir/c.py", "dir/d.py"],
        ]
        sources = resolve_sources(
            directory,
            Sources(
                globs=[
                    Glob(["dir/**/*.py", "other_dir/*.py"], ["dir/*.py"]),
                    Glob(["dir/*.py"], []),
                ]
            ),
        )
        self.assert_paths_match(
            sources,
            [
                "/project/dir/c.py",
                "/project/dir/d.py",
                "/project/dir/foo/e.py",
                "/project/dir/foo/f.py",
                "/project/other_dir/g.py",
            ],
        )
        mock_list.assert_has_calls(
            [
                call(
                    "/project", ["dir/**/*.py", "other_dir/*.py"], exclude=["dir/*.py"]
                ),
                call("/project", ["dir/*.py"], exclude=[]),
            ]
        )
        mock_list.clear()

        # Globs and regular files work together.
        mock_list.side_effect = [["dir/c.py", "dir/d.py"], ["other_dir/g.py"]]
        sources = resolve_sources(
            directory,
            Sources(
                files=["a.py", "b.py"],
                globs=[Glob(["dir/*.py"], []), Glob(["other_dir/*.py"], [])],
            ),
        )
        self.assert_paths_match(
            sources,
            [
                "/project/a.py",
                "/project/b.py",
                "/project/dir/c.py",
                "/project/dir/d.py",
                "/project/other_dir/g.py",
            ],
        )
        mock_list.assert_has_calls(
            [
                call("/project", ["dir/*.py"], exclude=[]),
                call("/project", ["other_dir/*.py"], exclude=[]),
            ]
        )
