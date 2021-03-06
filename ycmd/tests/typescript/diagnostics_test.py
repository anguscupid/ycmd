# Copyright (C) 2017 ycmd contributors
#
# This file is part of ycmd.
#
# ycmd is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ycmd is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ycmd.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import absolute_import
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division
from future import standard_library
standard_library.install_aliases()
from builtins import *  # noqa

from hamcrest import ( assert_that, contains, contains_inanyorder, has_entries,
                       has_entry )

from ycmd.tests.typescript import PathToTestFile, SharedYcmd
from ycmd.tests.test_utils import BuildRequest, LocationMatcher, RangeMatcher
from ycmd.utils import ReadFile


@SharedYcmd
def Diagnostics_FileReadyToParse_test( app ):
  filepath = PathToTestFile( 'test.ts' )
  contents = ReadFile( filepath )

  event_data = BuildRequest( filepath = filepath,
                             filetype = 'typescript',
                             contents = contents,
                             event_name = 'BufferVisit' )
  app.post_json( '/event_notification', event_data )

  event_data = BuildRequest( filepath = filepath,
                             filetype = 'typescript',
                             contents = contents,
                             event_name = 'FileReadyToParse' )

  assert_that(
    app.post_json( '/event_notification', event_data ).json,
    contains_inanyorder(
      has_entries( {
        'kind': 'ERROR',
        'text': "Property 'm' does not exist on type 'Foo'.",
        'location': LocationMatcher( filepath, 17, 5 ),
        'location_extent': RangeMatcher( filepath, ( 17, 5 ), ( 17, 6 ) ),
        'ranges': contains( RangeMatcher( filepath, ( 17, 5 ), ( 17, 6 ) ) ),
        'fixit_available': False
      } ),
      has_entries( {
        'kind': 'ERROR',
        'text': "Property 'nonExistingMethod' does not exist on type 'Bar'.",
        'location': LocationMatcher( filepath, 35, 5 ),
        'location_extent': RangeMatcher( filepath, ( 35, 5 ), ( 35, 22 ) ),
        'ranges': contains( RangeMatcher( filepath, ( 35, 5 ), ( 35, 22 ) ) ),
        'fixit_available': False
      } ),
      has_entries( {
        'kind': 'ERROR',
        'text': 'Expected 1-2 arguments, but got 0.',
        'location': LocationMatcher( filepath, 37, 1 ),
        'location_extent': RangeMatcher( filepath, ( 37, 1 ), ( 37, 12 ) ),
        'ranges': contains( RangeMatcher( filepath, ( 37, 1 ), ( 37, 12 ) ) ),
        'fixit_available': False
      } ),
    )
  )


@SharedYcmd
def Diagnostics_DetailedDiagnostics_test( app ):
  filepath = PathToTestFile( 'test.ts' )
  contents = ReadFile( filepath )

  event_data = BuildRequest( filepath = filepath,
                             filetype = 'typescript',
                             contents = contents,
                             event_name = 'BufferVisit' )
  app.post_json( '/event_notification', event_data )

  diagnostic_data = BuildRequest( filepath = filepath,
                                  filetype = 'typescript',
                                  contents = contents,
                                  line_num = 35,
                                  column_num = 6 )

  assert_that(
    app.post_json( '/detailed_diagnostic', diagnostic_data ).json,
    has_entry(
      'message', "Property 'nonExistingMethod' does not exist on type 'Bar'."
    )
  )
