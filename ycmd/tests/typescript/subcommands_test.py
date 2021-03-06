# encoding: utf-8
#
# Copyright (C) 2015 ycmd contributors
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
# Not installing aliases from python-future; it's unreliable and slow.
from builtins import *  # noqa

from hamcrest import assert_that, contains, contains_inanyorder, has_entries
from nose.tools import eq_
import requests
import pprint

from ycmd.tests.typescript import PathToTestFile, SharedYcmd
from ycmd.tests.test_utils import ( BuildRequest,
                                    ChunkMatcher,
                                    ErrorMatcher,
                                    LocationMatcher,
                                    MessageMatcher )
from ycmd.utils import ReadFile


def RunTest( app, test ):
  contents = ReadFile( test[ 'request' ][ 'filepath' ] )

  def CombineRequest( request, data ):
    kw = request
    request.update( data )
    return BuildRequest( **kw )

  app.post_json(
    '/event_notification',
    CombineRequest( test[ 'request' ], {
      'contents': contents,
      'filetype': 'typescript',
      'event_name': 'BufferVisit'
    } )
  )

  # We ignore errors here and check the response code ourself.
  # This is to allow testing of requests returning errors.
  response = app.post_json(
    '/run_completer_command',
    CombineRequest( test[ 'request' ], {
      'contents': contents,
      'filetype': 'typescript',
      'command_arguments': ( [ test[ 'request' ][ 'command' ] ]
                             + test[ 'request' ].get( 'arguments', [] ) )
    } ),
    expect_errors = True
  )

  print( 'completer response: {0}'.format( pprint.pformat( response.json ) ) )

  eq_( response.status_code, test[ 'expect' ][ 'response' ] )

  assert_that( response.json, test[ 'expect' ][ 'data' ] )


@SharedYcmd
def Subcommands_DefinedSubcommands_test( app ):
  subcommands_data = BuildRequest( completer_target = 'typescript' )

  assert_that(
    app.post_json( '/defined_subcommands', subcommands_data ).json,
    contains_inanyorder(
      'GoTo',
      'GoToDeclaration',
      'GoToDefinition',
      'GoToType',
      'GetDoc',
      'GetType',
      'GoToReferences',
      'RefactorRename',
      'RestartServer'
    )
  )


@SharedYcmd
def Subcommands_GetType_Basic_test( app ):
  RunTest( app, {
    'description': 'GetType works on a variable',
    'request': {
      'command': 'GetType',
      'line_num': 17,
      'column_num': 1,
      'filepath': PathToTestFile( 'test.ts' ),
    },
    'expect': {
      'response': requests.codes.ok,
      'data': MessageMatcher( 'var foo: Foo' )
    }
  } )


@SharedYcmd
def Subcommands_GetType_HasNoType_test( app ):
  RunTest( app, {
    'description': 'GetType returns an error on a keyword',
    'request': {
      'command': 'GetType',
      'line_num': 2,
      'column_num': 1,
      'filepath': PathToTestFile( 'test.ts' ),
    },
    'expect': {
      'response': requests.codes.internal_server_error,
      'data': ErrorMatcher( RuntimeError, 'No content available.' )
    }
  } )


@SharedYcmd
def Subcommands_GetDoc_Method_test( app ):
  RunTest( app, {
    'description': 'GetDoc on a method returns its docstring',
    'request': {
      'command': 'GetDoc',
      'line_num': 34,
      'column_num': 9,
      'filepath': PathToTestFile( 'test.ts' ),
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
         'detailed_info': '(method) Bar.testMethod(): void\n\n'
                          'Method documentation'
      } )
    }
  } )


@SharedYcmd
def Subcommands_GetDoc_Class_test( app ):
  RunTest( app, {
    'description': 'GetDoc on a class returns its docstring',
    'request': {
      'command': 'GetDoc',
      'line_num': 37,
      'column_num': 2,
      'filepath': PathToTestFile( 'test.ts' ),
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
         'detailed_info': 'class Bar\n\n'
                          'Class documentation\n\n'
                          'Multi-line'
      } )
    }
  } )


@SharedYcmd
def Subcommands_GetDoc_Class_Unicode_test( app ):
  RunTest( app, {
    'description': 'GetDoc works with Unicode characters',
    'request': {
      'command': 'GetDoc',
      'line_num': 35,
      'column_num': 12,
      'filepath': PathToTestFile( 'unicode.ts' ),
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
         'detailed_info': 'class Båøz\n\n'
                          'Test unicøde st††††',
      } )
    }
  } )


@SharedYcmd
def Subcommands_GoToReferences_test( app ):
  RunTest( app, {
    'description': 'GoToReferences works',
    'request': {
      'command': 'GoToReferences',
      'line_num': 33,
      'column_num': 6,
      'filepath': PathToTestFile( 'test.ts' ),
    },
    'expect': {
      'response': requests.codes.ok,
      'data': contains_inanyorder(
        has_entries( { 'description': 'var bar = new Bar();',
                       'line_num'   : 33,
                       'column_num' : 5,
                       'filepath'   : PathToTestFile( 'test.ts' ) } ),
        has_entries( { 'description': 'bar.testMethod();',
                       'line_num'   : 34,
                       'column_num' : 1,
                       'filepath'   : PathToTestFile( 'test.ts' ) } ),
        has_entries( { 'description': 'bar.nonExistingMethod();',
                       'line_num'   : 35,
                       'column_num' : 1,
                       'filepath'   : PathToTestFile( 'test.ts' ) } ),
        has_entries( { 'description': 'var bar = new Bar();',
                       'line_num'   : 1,
                       'column_num' : 5,
                       'filepath'   : PathToTestFile( 'file3.ts' ) } ),
        has_entries( { 'description': 'bar.testMethod();',
                       'line_num'   : 2,
                       'column_num' : 1,
                       'filepath'   : PathToTestFile( 'file3.ts' ) } )
      )
    }
  } )


@SharedYcmd
def Subcommands_GoToReferences_Unicode_test( app ):
  RunTest( app, {
    'description': 'GoToReferences works with Unicode characters',
    'request': {
      'command': 'GoToReferences',
      'line_num': 14,
      'column_num': 3,
      'filepath': PathToTestFile( 'unicode.ts' ),
    },
    'expect': {
      'response': requests.codes.ok,
      'data': contains_inanyorder(
        has_entries( { 'description': '  å: number;',
                       'line_num'   : 14,
                       'column_num' : 3,
                       'filepath'   : PathToTestFile( 'unicode.ts' ) } ),
        has_entries( { 'description': 'var baz = new Bår(); baz.å;',
                       'line_num'   : 20,
                       'column_num' : 27,
                       'filepath'   : PathToTestFile( 'unicode.ts' ) } ),
        has_entries( { 'description': 'baz.å;',
                       'line_num'   : 23,
                       'column_num' : 5,
                       'filepath'   : PathToTestFile( 'unicode.ts' ) } ),
        has_entries( { 'description': 'føø_long_long.å;',
                       'line_num'   : 27,
                       'column_num' : 17,
                       'filepath'   : PathToTestFile( 'unicode.ts' ) } )
      )
    }
  } )


@SharedYcmd
def Subcommands_GoTo_Basic( app, goto_command ):
  RunTest( app, {
    'description': goto_command + ' works within file',
    'request': {
      'command': goto_command,
      'line_num': 34,
      'column_num': 8,
      'filepath': PathToTestFile( 'test.ts' ),
    },
    'expect': {
      'response': requests.codes.ok,
      'data': LocationMatcher( PathToTestFile( 'test.ts' ), 30, 3 )
    }
  } )


def Subcommands_GoTo_Basic_test():
  for command in [ 'GoTo', 'GoToDefinition', 'GoToDeclaration' ]:
    yield Subcommands_GoTo_Basic, command


@SharedYcmd
def Subcommands_GoTo_Unicode( app, goto_command ):
  RunTest( app, {
    'description': goto_command + ' works with Unicode characters',
    'request': {
      'command': goto_command,
      'line_num': 28,
      'column_num': 19,
      'filepath': PathToTestFile( 'unicode.ts' ),
    },
    'expect': {
      'response': requests.codes.ok,
      'data': LocationMatcher( PathToTestFile( 'unicode.ts' ), 15, 3 )
    }
  } )


def Subcommands_GoTo_Unicode_test():
  for command in [ 'GoTo', 'GoToDefinition', 'GoToDeclaration' ]:
    yield Subcommands_GoTo_Unicode, command


@SharedYcmd
def Subcommands_GoTo_Fail( app, goto_command ):
  RunTest( app, {
    'description': goto_command + ' fails on non-existing method',
    'request': {
      'command': goto_command,
      'line_num': 35,
      'column_num': 6,
      'filepath': PathToTestFile( 'test.ts' ),
    },
    'expect': {
      'response': requests.codes.internal_server_error,
      'data': ErrorMatcher( RuntimeError, 'Could not find definition.' )
    }
  } )


def Subcommands_GoTo_Fail_test():
  for command in [ 'GoTo', 'GoToDefinition', 'GoToDeclaration' ]:
    yield Subcommands_GoTo_Fail, command


@SharedYcmd
def Subcommands_GoToType_test( app ):
  RunTest( app, {
    'description': 'GoToType works',
    'request': {
      'command': 'GoToType',
      'line_num': 14,
      'column_num': 6,
      'filepath': PathToTestFile( 'test.ts' ),
    },
    'expect': {
      'response': requests.codes.ok,
      'data': LocationMatcher( PathToTestFile( 'test.ts' ), 2, 7 )
    }
  } )


@SharedYcmd
def Subcommands_GoToType_Fail_test( app ):
  RunTest( app, {
    'description': 'GoToType fails outside the buffer',
    'request': {
      'command': 'GoToType',
      'line_num': 39,
      'column_num': 8,
      'filepath': PathToTestFile( 'test.ts' ),
    },
    'expect': {
      'response': requests.codes.internal_server_error,
      'data': ErrorMatcher( RuntimeError, 'Could not find type definition.' )
    }
  } )


@SharedYcmd
def Subcommands_RefactorRename_Missing_test( app ):
  RunTest( app, {
    'description': 'RefactorRename requires a parameter',
    'request': {
      'command': 'RefactorRename',
      'line_num': 30,
      'column_num': 6,
      'filepath': PathToTestFile( 'test.ts' ),
    },
    'expect': {
      'response': requests.codes.internal_server_error,
      'data': ErrorMatcher( ValueError,
                            'Please specify a new name to rename it to.\n'
                            'Usage: RefactorRename <new name>' )
    }
  } )


@SharedYcmd
def Subcommands_RefactorRename_NotPossible_test( app ):
  RunTest( app, {
    'description': 'RefactorRename cannot rename a non-existing method',
    'request': {
      'command': 'RefactorRename',
      'arguments': [ 'whatever' ],
      'line_num': 35,
      'column_num': 5,
      'filepath': PathToTestFile( 'test.ts' ),
    },
    'expect': {
      'response': requests.codes.internal_server_error,
      'data': ErrorMatcher( RuntimeError,
                            'Value cannot be renamed: '
                            'You cannot rename this element.' )
    }
  } )


@SharedYcmd
def Subcommands_RefactorRename_Simple_test( app ):
  RunTest( app, {
    'description': 'RefactorRename works on a class name',
    'request': {
      'command': 'RefactorRename',
      'arguments': [ 'test' ],
      'line_num': 2,
      'column_num': 8,
      'filepath': PathToTestFile( 'test.ts' ),
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'fixits': contains( has_entries( {
          'chunks': contains_inanyorder(
            ChunkMatcher(
              'test',
              LocationMatcher( PathToTestFile( 'test.ts' ), 14, 15 ),
              LocationMatcher( PathToTestFile( 'test.ts' ), 14, 18 ) ),
            ChunkMatcher(
              'test',
              LocationMatcher( PathToTestFile( 'test.ts' ), 2, 7 ),
              LocationMatcher( PathToTestFile( 'test.ts' ), 2, 10 ) ),
          ),
          'location': LocationMatcher( PathToTestFile( 'test.ts' ), 2, 8 )
        } ) )
      } )
    }
  } )


@SharedYcmd
def Subcommands_RefactorRename_MultipleFiles_test( app ):
  RunTest( app, {
    'description': 'RefactorRename works across files',
    'request': {
      'command': 'RefactorRename',
      'arguments': [ 'this-is-a-longer-string' ],
      'line_num': 25,
      'column_num': 9,
      'filepath': PathToTestFile( 'test.ts' ),
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'fixits': contains( has_entries( {
          'chunks': contains_inanyorder(
            ChunkMatcher(
              'this-is-a-longer-string',
              LocationMatcher( PathToTestFile( 'test.ts' ), 25, 7 ),
              LocationMatcher( PathToTestFile( 'test.ts' ), 25, 10 ) ),
            ChunkMatcher(
              'this-is-a-longer-string',
              LocationMatcher( PathToTestFile( 'test.ts' ), 33, 15 ),
              LocationMatcher( PathToTestFile( 'test.ts' ), 33, 18 ) ),
            ChunkMatcher(
              'this-is-a-longer-string',
              LocationMatcher( PathToTestFile( 'test.ts' ), 37, 1 ),
              LocationMatcher( PathToTestFile( 'test.ts' ), 37, 4 ) ),
            ChunkMatcher(
              'this-is-a-longer-string',
              LocationMatcher( PathToTestFile( 'file2.ts' ), 1, 5 ),
              LocationMatcher( PathToTestFile( 'file2.ts' ), 1, 8 ) ),
            ChunkMatcher(
              'this-is-a-longer-string',
              LocationMatcher( PathToTestFile( 'file3.ts' ), 1, 15 ),
              LocationMatcher( PathToTestFile( 'file3.ts' ), 1, 18 ) ),
          ),
          'location': LocationMatcher( PathToTestFile( 'test.ts' ), 25, 9 )
        } ) )
      } )
    }
  } )


@SharedYcmd
def Subcommands_RefactorRename_SimpleUnicode_test( app ):
  RunTest( app, {
    'description': 'RefactorRename works with Unicode characters',
    'request': {
      'command': 'RefactorRename',
      'arguments': [ 'ø' ],
      'line_num': 14,
      'column_num': 3,
      'filepath': PathToTestFile( 'unicode.ts' ),
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'fixits': contains( has_entries( {
          'chunks': contains_inanyorder(
            ChunkMatcher(
              'ø',
              LocationMatcher( PathToTestFile( 'unicode.ts' ), 14, 3 ),
              LocationMatcher( PathToTestFile( 'unicode.ts' ), 14, 5 ) ),
            ChunkMatcher(
              'ø',
              LocationMatcher( PathToTestFile( 'unicode.ts' ), 20, 27 ),
              LocationMatcher( PathToTestFile( 'unicode.ts' ), 20, 29 ) ),
            ChunkMatcher(
              'ø',
              LocationMatcher( PathToTestFile( 'unicode.ts' ), 23, 5 ),
              LocationMatcher( PathToTestFile( 'unicode.ts' ), 23, 7 ) ),
            ChunkMatcher(
              'ø',
              LocationMatcher( PathToTestFile( 'unicode.ts' ), 27, 17),
              LocationMatcher( PathToTestFile( 'unicode.ts' ), 27, 19 ) ),
          ),
          'location': LocationMatcher( PathToTestFile( 'unicode.ts' ), 14, 3 )
        } ) )
      } )
    }
  } )
