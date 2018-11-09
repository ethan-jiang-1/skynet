#!/usr/bin/env python
import subprocess
import os
import sys


class ConsoleColor(object):
    RED = "\033[1;31m"
    BLUE = "\033[1;34m"
    CYAN = "\033[1;36m"
    GREEN = "\033[0;32m"
    RESET = "\033[0;0m"
    BOLD = "\033[;1m"
    REVERSE = "\033[;7m"

    def __init__(self, cc_color):
        self.cc_color = cc_color

    def __enter__(self):
        sys.stdout.write(self.cc_color)

    def __exit__(self, *args):
        sys.stdout.write(ConsoleColor.RESET)


class CwdContext(object):
    def __init__(self):
        self.org_dir = os.getcwd()

    def __enter__(self):
        dir_name = os.path.dirname(__file__)
        if len(dir_name) != 0:
            new_dir = os.path.normpath(self.org_dir + "/" + dir_name)
            os.chdir(new_dir)

    def __exit__(self, *args):
        os.chdir(self.org_dir)


class LineProcess(object):
    @classmethod
    def split_paths(cls, paths_line, sept):
        return paths_line.split(sept)

    @classmethod
    def split_paths_with_lead(cls, lead_paths_line, sept):
        paths_line = cls._extract_paths(lead_paths_line)
        return cls.split_paths(paths_line, sept)

    @classmethod
    def _extract_paths(cls, line):
        line = line.replace("\'", "")
        line = line.replace("\n", "")
        lead, rest = line.split("=")
        return rest


class Main(object):
    def __init__(self):
        self.luarocks_lua_paths = []
        self.luarocks_lua_cpaths = []
        self.luarocks_paths = []
        self.prj_lua_paths = []
        self.prj_lua_cpaths = []
        self.org_paths = {}
        self.new_paths = {}

    def find_luarocks_paths(self):
        command = ["luarocks", "path"]
        p = subprocess.Popen(command,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT)
        stdout_lines = p.stdout.readlines()

        for line in stdout_lines:
            if line.startswith("export LUA_PATH="):
                self.org_paths["LUA_PATH"] = line.replace("\n", "")
                self.luarocks_lua_paths = LineProcess.split_paths_with_lead(line, ";")
            elif line.startswith("export LUA_CPATH="):
                self.org_paths["LUA_CPATH"] = line.replace("\n", "")
                self.luarocks_lua_cpaths = LineProcess.split_paths_with_lead(line, ";")
            elif line.startswith("export PATH="):
                self.org_paths["PATH"] = line.replace("\n", "")
                self.luarocks_paths = LineProcess.split_paths_with_lead(line, ":")
            else:
                print("error: unknow line:" + str(line))

    def find_prj_paths(self):
        prj_dir = os.getcwd()
        self.prj_lua_paths.append(prj_dir + "/lualib/?.lua")
        # self.prj_lua_paths.append(prj_dir + "/dev/?.lua")
        if os.environ.get("HOME").startswith("/home/"):
           self.prj_lua_cpaths.append(prj_dir + "/luaclib/?.so")
        # elif os.environ.get("HOME").startswith("/User/"):
        #    self.prj_lua_cpaths.append(prj_dir + "/dev/runtime/macos/?.so")

    def diff_paths(self):
        env_paths = LineProcess.split_paths(os.environ.get("PATH"), ":")
        set_diff = set(self.luarocks_paths).difference(set(env_paths))
        if len(set_diff) == 0:
            print("PATH is ok, no change need")
        else:
            print("PATH different is " + str(set_diff))
        return "PATH", ":", set_diff

    def diff_lua_paths(self):
        if os.environ.get("LUA_PATH") is None:
            print("No LUA_PATH found, please reinstall lua")
            sys.exit(-1)

        env_lua_paths = LineProcess.split_paths(os.environ.get("LUA_PATH"), ";")

        lua_paths = []
        lua_paths.extend(self.luarocks_lua_paths)
        lua_paths.extend(self.prj_lua_paths)
        set_diff = set(lua_paths).difference(set(env_lua_paths))
        if len(set_diff) == 0:
            print("LUA_PATH is ok, no change need")
        else:
            print("LUA_PATH different is " + str(set_diff))
        return "LUA_PATH", ";", set_diff

    def diff_lua_cpaths(self):
        if os.environ.get("LUA_CPATH") is None:
            print("No LUA_CPATH found, please reinstall lua")
            sys.exit(-1)

        env_lua_cpaths = LineProcess.split_paths(os.environ.get("LUA_CPATH"), ";")

        lua_cpaths = []
        lua_cpaths.extend(self.luarocks_lua_cpaths)
        lua_cpaths.extend(self.prj_lua_cpaths)
        set_diff = set(lua_cpaths).difference(set(env_lua_cpaths))
        if len(set_diff) == 0:
            print("LUA_CPATH is ok, no change need")
        else:
            print("LUA_CPATH different is " + str(set_diff))
        return "LUA_CPATH", ";", set_diff

    def fix_paths(self, diff_func):
        name, sep, set_diff = diff_func()
        if len(set_diff) != 0:
            insert_line = sep.join(list(set_diff))
            org_line = self.org_paths[name]
            new_line = org_line.replace("='", "='" + insert_line + sep)
            self.new_paths[name] = new_line

    def run(self):
        print("Find out what lua paths update required for the project...")

        self.find_luarocks_paths()
        self.find_prj_paths()

        self.fix_paths(self.diff_paths)
        self.fix_paths(self.diff_lua_paths)
        self.fix_paths(self.diff_lua_cpaths)

        if len(self.new_paths) != 0:
            with ConsoleColor(ConsoleColor.CYAN):
                print("Updated required, New ENV are: -- please simple copy into your rc file (~/.bashrc for linux)")
                print("")
                fh = open("skynet_env.sh", "w+")
                if fh is not None:
                    fh.write("#!/bin/bash\n")
                for name, value in self.new_paths.items():
                    print(value)
                    if fh is not None:
                        fh.write(value + "\n")
                print("")
                if fh is not None:
                    fh.close()

                print("exec: source skynet_env.sh to setup env")
        else:
            with ConsoleColor(ConsoleColor.GREEN):
                print("No need to update ENV variables, the env is ok.")

        return 0


if __name__ == '__main__':
    with CwdContext():
        rc = Main().run()
        exit(rc)
