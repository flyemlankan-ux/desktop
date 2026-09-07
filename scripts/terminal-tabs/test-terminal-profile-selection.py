#!/usr/bin/env python3
"""Prove ordinary profile selection using the FINAL installed Zen Terminal path.

Run with the existing test-only marionette_driver environment. Never installs an
app, opens stock Zen, or reads a personal profile. Every generated profile and
HOME lives in a private system temporary directory outside the repository.

macOS Firefox uses FSFindFolder, so HOME alone is NOT relied on for isolation.
MOZ_APP_DATA and MOZ_LOCAL_APP_DATA explicitly redirect all profile storage.
The compiled App.Profile metadata is checked separately before launch.

Only this synthetic test bypasses the copy utility's global 'any Zen running'
process-name guard. Actual open-file, profile-lock, source/destination, engine,
verification and no-overwrite checks remain enabled. Production code is unchanged.
"""
import argparse
import configparser
import importlib.util
import json
import os
from pathlib import Path
import plistlib
import re
import socket
import subprocess
import sys
import tempfile
import time
from unittest import mock


def read_ini(path):
    parser = configparser.ConfigParser(interpolation=None)
    parser.optionxform = str
    with path.open(encoding="utf-8") as stream:
        parser.read_file(stream)
    return parser


def assert_inside(path, root):
    path = Path(path).resolve()
    assert root == path or root in path.parents, "Test browser escaped its synthetic HOME"
    return path


def wait_for(check, label, timeout=40):
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        try:
            value = check()
            if value:
                return value
        except Exception as error:
            last = error
        time.sleep(0.1)
    raise AssertionError(f"Timed out waiting for {label}: {last}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", type=Path, required=True,
                        help="Final installed .app path; it is launched in place, never copied or changed.")
    parser.add_argument("--expected-engine", default="155.0.1")
    parser.add_argument("--port", type=int, default=2833)
    args = parser.parse_args()
    if sys.platform != "darwin":
        parser.error("This proof requires macOS.")
    if args.app.is_symlink():
        parser.error("Use the real final app path, not a symlink.")
    app = args.app.resolve(strict=True)
    info = plistlib.loads((app / "Contents/Info.plist").read_bytes())
    assert info["CFBundleIdentifier"] == "app.zen-browser.zen-terminal", "Refusing to launch a stock or unrelated app"
    assert info["CFBundleExecutable"] == "zen-terminal"
    executable = app / "Contents/MacOS/zen-terminal"
    assert executable.is_file() and not executable.is_symlink()
    app_ini = read_ini(app / "Contents/Resources/application.ini")
    platform_ini = read_ini(app / "Contents/Resources/platform.ini")
    assert app_ini["App"]["Profile"] == "zen-terminal", "Compiled browser profile root is not isolated"
    assert platform_ini["Build"]["Milestone"] == args.expected_engine, "Wrong actual packaged engine"
    assert 1024 <= args.port <= 65535 and args.port != 2831
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", args.port))

    from marionette_driver.marionette import Marionette

    copy_script = Path(__file__).with_name("copy-zen-profiles.py")
    spec = importlib.util.spec_from_file_location("synthetic_profile_copy", copy_script)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    report = {"app": str(app), "engine": args.expected_engine,
              "test_data": "synthetic only; no personal profile access",
              "profile_selection_flags": "none on either launch",
              "isolation": "HOME plus explicit MOZ_APP_DATA and MOZ_LOCAL_APP_DATA",
              "copy_guard_difference": "only global Zen process-name rejection bypassed; real lsof and profile locks retained",
              "checks": []}
    process = None
    client = None
    owned_session = False
    with tempfile.TemporaryDirectory(prefix="zen-profile-selection-proof-") as temporary:
        run = Path(temporary).resolve()
        repository = Path(__file__).resolve().parents[2]
        assert repository not in run.parents and run != repository
        home = run / "home"
        home.mkdir(mode=0o700)
        data = home / "Library/Application Support/zen-terminal"
        local_data = home / "Library/Caches/zen-terminal"
        data.parent.mkdir(parents=True, mode=0o700)
        local_data.parent.mkdir(parents=True, mode=0o700)
        (home / ".zshenv").write_text("export PATH=/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin\n")
        preferences = {
            "marionette.port": args.port,
            "browser.shell.checkDefaultBrowser": False,
            "browser.startup.page": 0,
            "browser.startup.homepage": "about:blank",
            "browser.aboutwelcome.enabled": False,
            "zen.welcome-screen.seen": True,
            "app.update.disabledForTesting": True,
            "app.update.auto": False,
            "app.update.enabled": False,
            "datareporting.policy.dataSubmissionEnabled": False,
        }
        environment = dict(os.environ)
        for key in ["MOZ_PROFILE_PATH", "MOZ_PROFILE_LOCAL_PATH", "MOZ_PROFILE_NAME",
                    "MOZ_LEGACY_PROFILES", "MOZ_RESET_PROFILE_RESTART", "MOZ_RESTARTED"]:
            environment.pop(key, None)
        environment.update(HOME=str(home), ZDOTDIR=str(home), SHELL="/bin/zsh",
                           MOZ_APP_DATA=str(data), MOZ_LOCAL_APP_DATA=str(local_data),
                           MOZ_NO_REMOTE="1", MOZ_MARIONETTE="1",
                           MOZ_MARIONETTE_PREF_STATE_ACROSS_RESTARTS=json.dumps(preferences))
        log = (run / "browser.log").open("w")

        def js(script):
            return client.execute_script(script)

        def launch():
            nonlocal process, client, owned_session
            # Deliberately no -profile, -P, or -CreateProfile flag.
            process = subprocess.Popen([str(executable), "-no-remote", "-marionette",
                                        "--remote-allow-system-access"],
                                       env=environment, stdout=log, stderr=log)
            client = Marionette(host="127.0.0.1", port=args.port,
                                socket_timeout=30, startup_timeout=40)
            client.raise_for_port(timeout=40)
            client.start_session()
            client.set_context("chrome")
            assert js("return Services.appinfo.processID;") == process.pid, "Automation connected to a process this test does not own"
            owned_session = True
            wait_for(lambda: js("return Boolean(window.gBrowserInit?.delayedStartupFinished);"), "normal browser startup")
            actual = js("return {data:Services.dirsvc.get('UAppData',Ci.nsIFile).path,profile:Services.dirsvc.get('ProfD',Ci.nsIFile).path,engine:Services.appinfo.platformVersion};")
            assert assert_inside(actual["data"], home) == data
            assert_inside(actual["profile"], data)
            assert Path(actual["data"]).name == "zen-terminal"
            assert actual["engine"] == args.expected_engine
            return actual

        def stop():
            nonlocal process, client, owned_session
            if process is None:
                return
            if process.poll() is None and client is not None and owned_session:
                try:
                    js("Services.startup.quit(Ci.nsIAppStartup.eAttemptQuit);")
                except Exception:
                    pass  # Expected connection closure during a normal quit.
            try:
                process.wait(timeout=25)
            except subprocess.TimeoutExpired:
                process.terminate()  # Only the exact Popen child, never pkill.
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
                raise AssertionError("Test-owned browser did not quit normally")
            finally:
                client = None
                owned_session = False
            assert process.returncode == 0, "Test-owned browser exited abnormally"
            process = None

        try:
            first = launch()
            report["checks"].append("blank ordinary launch stayed inside synthetic profile storage")
            first_profile = assert_inside(first["profile"], home)
            stop()
            generated = read_ini(data / "profiles.ini")
            sections = [section for section in generated.sections()
                        if re.fullmatch(r"Install[0-9A-Fa-f]{16}", section)]
            assert len(sections) == 1, "Blank probe did not identify one dedicated installation"
            install_hash = sections[0][len("Install"):]
            assert (data / generated[sections[0]]["Default"]).resolve() == first_profile
            compatibility = read_ini(first_profile / "compatibility.ini")
            compatibility["Compatibility"]["LastAppDir"] = str(run / "different-original-app/Contents/Resources/browser")
            # Retain the generated first-launch tree privately, leaving a fresh
            # destination for the production copy utility's no-overwrite rule.
            data.rename(run / "blank-probe-data")
            source = run / "synthetic-source"
            source.mkdir(mode=0o700)
            marker = "synthetic-intended-profile"
            names = {"intended": "Synthetic intended", "other": "Synthetic other", "unused": "Synthetic unused"}
            source_ini = configparser.ConfigParser(interpolation=None)
            source_ini.optionxform = str
            source_ini["General"] = {"StartWithLastProfile": "1", "Version": "2"}
            for index, (relative, name) in enumerate(names.items()):
                profile = source / "Profiles" / relative
                profile.mkdir(parents=True, mode=0o700)
                source_ini[f"Profile{index}"] = {"Name": name, "IsRelative": "1", "Path": f"Profiles/{relative}", "Default": "1" if relative == "other" else "0"}
                (profile / "times.json").write_text('{"created":1,"synthetic":true}\n')
                if relative != "unused":
                    with (profile / "compatibility.ini").open("w") as stream:
                        compatibility.write(stream)
                    (profile / ".parentlock").touch()
                    value = marker if relative == "intended" else "synthetic-other-profile"
                    (profile / "prefs.js").write_text(f'user_pref("zen.terminal.profileSelectionTestMarker", {json.dumps(value)});\n')
            source_ini["Install0000000000000000"] = {"Default": "Profiles/intended", "Locked": "1"}
            with (source / "profiles.ini").open("w") as stream:
                source_ini.write(stream)
            source_hashes = {p.relative_to(source).as_posix(): migration.digest(p) for p in source.rglob("*") if p.is_file()}
            real_run = subprocess.run

            def synthetic_activity_check(checked_source):
                assert Path(checked_source) == source and run in source.parents
                assert process is None, "Test-owned browser must be stopped before copying"
                def filter_only_global_process_guard(command, **kwargs):
                    result = real_run(command, **kwargs)
                    if command == ["/bin/ps", "-axo", "pid=,comm="]:
                        result.stdout = "\n".join(line for line in result.stdout.splitlines()
                            if not (len(line.strip().split(None, 1)) == 2 and
                                    Path(line.strip().split(None, 1)[1]).name.lower() in {"zen", "zen-bin"}))
                    return result
                with mock.patch.object(migration.subprocess, "run", side_effect=filter_only_global_process_guard):
                    migration.ensure_closed(checked_source)

            result = migration.copy_setup(source, data, args.expected_engine, args.expected_engine,
                                          default_profile="Synthetic intended", copy=True,
                                          activity_check=synthetic_activity_check,
                                          target_install_hash=install_hash)
            assert result["profile_count"] == 3
            assert result["profile_selection"] == "dedicated-install"
            report["checks"].append("production copier generated the final installation mapping with real locks and open-file checks")
            second = launch()
            assert Path(second["profile"]).resolve() == data / "Profiles/intended"
            assert js('return Services.prefs.getStringPref("zen.terminal.profileSelectionTestMarker", "missing");') == marker
            registered = js("const service=Cc['@mozilla.org/toolkit/profile-service;1'].getService(Ci.nsIToolkitProfileService);const names=[];const e=service.profiles;while(e.hasMoreElements()){names.push(e.getNext().QueryInterface(Ci.nsIToolkitProfile).name);}return names;")
            assert sorted(registered) == sorted(names.values()), "Some copied profiles were lost or a blank replacement was created"
            report["checks"].append("ordinary relaunch selected the intended copied profile despite a different source LastAppDir")
            report["checks"].append("all three copied profiles remained registered, including the unused profile")
            stop()
            assert source_hashes == {p.relative_to(source).as_posix(): migration.digest(p) for p in source.rglob("*") if p.is_file()}
            report["checks"].append("synthetic source bytes remained unchanged")
            report["target_install_hash"] = install_hash.upper()
            report["result"] = "pass"
            print(json.dumps(report, indent=2))
        finally:
            try:
                if process is not None:
                    stop()
            finally:
                log.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
