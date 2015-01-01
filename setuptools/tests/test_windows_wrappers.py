"""
Python Script Wrapper for Windows
=================================

setuptools includes wrappers for Python scripts that allows them to be
executed like regular windows programs.  There are 2 wrappers, once
for command-line programs, cli.exe, and one for graphical programs,
gui.exe.  These programs are almost identical, function pretty much
the same way, and are generated from the same source file.  The
wrapper programs are used by copying them to the directory containing
the script they are to wrap and with the same name as the script they
are to wrap.
"""

import os, sys
import textwrap
import subprocess

import pytest

from setuptools.command.easy_install import nt_quote_arg
import pkg_resources


pytestmark = pytest.mark.skipif(sys.platform != 'win32', reason="Windows only")


class WrapperTester:
    @classmethod
    def create_script(cls, tempdir):
        """
        Create a simple script, foo-script.py

        Note that the script starts with a Unix-style '#!' line saying which
        Python executable to run.  The wrapper will use this line to find the
        correct Python executable.
        """

        sample_directory = tempdir
        script = cls.script_tmpl % dict(python_exe=nt_quote_arg
            (sys.executable))

        f = open(os.path.join(sample_directory, cls.script_name), 'w')
        f.write(script)
        f.close()

        # also copy cli.exe to the sample directory

        f = open(os.path.join(sample_directory, cls.wrapper_name), 'wb')
        f.write(
            pkg_resources.resource_string('setuptools', cls.wrapper_source)
            )
        f.close()


class TestCLI(WrapperTester):
    script_name = 'foo-script.py'
    wrapper_source = 'cli-32.exe'
    wrapper_name = 'foo.exe'
    script_tmpl = textwrap.dedent("""
        #!%(python_exe)s
        import sys
        input = repr(sys.stdin.read())
        print(sys.argv[0][-14:])
        print(sys.argv[1:])
        print(input)
        if __debug__:
            print('non-optimized')
        """).lstrip()

    def test_basic(self, tmpdir):
        """
        When the copy of cli.exe, foo.exe in this example, runs, it examines
        the path name it was run with and computes a Python script path name
        by removing the '.exe' suffix and adding the '-script.py' suffix. (For
        GUI programs, the suffix '-script-pyw' is added.)  This is why we
        named out script the way we did.  Now we can run out script by running
        the wrapper:

        This example was a little pathological in that it exercised windows
        (MS C runtime) quoting rules:

        - Strings containing spaces are surrounded by double quotes.

        - Double quotes in strings need to be escaped by preceding them with
          back slashes.

        - One or more backslashes preceding double quotes need to be escaped
          by preceding each of them with back slashes.
        """
        sample_directory = str(tmpdir)
        self.create_script(sample_directory)
        cmd = [os.path.join(sample_directory, 'foo.exe'), 'arg1', 'arg 2',
            'arg "2\\"', 'arg 4\\', 'arg5 a\\\\b']
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stdin=subprocess.PIPE)
        stdout, stderr = proc.communicate('hello\nworld\n'.encode('ascii'))
        actual = stdout.decode('ascii').replace('\r\n', '\n')
        expected = textwrap.dedent(r"""
            \foo-script.py
            ['arg1', 'arg 2', 'arg "2\\"', 'arg 4\\', 'arg5 a\\\\b']
            'hello\nworld\n'
            non-optimized
            """).lstrip()
        assert actual == expected

    def test_with_options(self, tmpdir):
        """
        Specifying Python Command-line Options
        --------------------------------------

        You can specify a single argument on the '#!' line.  This can be used
        to specify Python options like -O, to run in optimized mode or -i
        to start the interactive interpreter.  You can combine multiple
        options as usual. For example, to run in optimized mode and
        enter the interpreter after running the script, you could use -Oi:
        """
        sample_directory = str(tmpdir)
        self.create_script(sample_directory)
        f = open(os.path.join(sample_directory, 'foo-script.py'), 'w')
        f.write(textwrap.dedent("""
            #!%(python_exe)s  -Oi
            import sys
            input = repr(sys.stdin.read())
            print(sys.argv[0][-14:])
            print(sys.argv[1:])
            print(input)
            if __debug__:
                print('non-optimized')
            sys.ps1 = '---'
            """).lstrip() % dict(python_exe=nt_quote_arg(sys.executable)))
        f.close()
        cmd = [os.path.join(sample_directory, 'foo.exe')]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout, stderr = proc.communicate()
        actual = stdout.decode('ascii').replace('\r\n', '\n')
        expected = textwrap.dedent(r"""
            \foo-script.py
            []
            ''
            ---
            """).lstrip()
        assert actual == expected


class TestGUI(WrapperTester):
    """
    Testing the GUI Version
    -----------------------
    """
    script_name = 'bar-script.pyw'
    wrapper_source = 'gui-32.exe'
    wrapper_name = 'bar.exe'

    script_tmpl = textwrap.dedent("""
        #!%(python_exe)s
        import sys
        f = open(sys.argv[1], 'wb')
        bytes_written = f.write(repr(sys.argv[2]).encode('utf-8'))
        f.close()
        """).strip()

    def test_basic(self, tmpdir):
        """Test the GUI version with the simple scipt, bar-script.py"""
        sample_directory = str(tmpdir)
        self.create_script(sample_directory)

        cmd = [
            os.path.join(sample_directory, 'bar.exe'),
            os.path.join(sample_directory, 'test_output.txt'),
            'Test Argument',
        ]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout, stderr = proc.communicate()
        assert not stdout
        assert not stderr
        f_out = open(os.path.join(sample_directory, 'test_output.txt'), 'rb')
        assert f_out.read().decode('ascii') == repr('Test Argument')
        f_out.close()