""" """

import json
import sys
import threading
import importlib
import rpyc
import rpyc.utils.helpers
import rpyc.utils.server

from typing import TYPE_CHECKING, Optional, Any

import binaryninja  # type: ignore

from .helpers import (
    info,
    err,
    dbg,
)

from .constants import (
    DEFAULT_HOST_IP,
    DEFAULT_HOST_PORT,
    DEFAULT_TIMEOUT,
    SERVICE_NAME,
    SETTING_AUTOSTART,
    SETTING_RPYC_HOST,
    SETTING_RPYC_PORT,
    SETTING_RPYC_TIMEOUT,
)

if TYPE_CHECKING:
    import rpyc.core.protocol


G_SERVICETHREAD: Optional[threading.Thread] = None
G_SERVER: Optional[rpyc.utils.server.ThreadedServer] = None
__bv: Optional["binaryninja.binaryview.BinaryView"] = None


def register_settings() -> None:
    all_settings: dict[str, str] = {
        SETTING_AUTOSTART: f"""{{ "title" : "Auto Start", "description" : "Automatically start {SERVICE_NAME} when Binary Ninja opens", "type" : "boolean", "default" : false, "ignore" : ["SettingsProjectScope", "SettingsResourceScope"]}}""",
        SETTING_RPYC_HOST: f"""{{ "title" : "TCP Listen Host", "description" : "Interface {SERVICE_NAME} should listen", "type" : "string", "default" : "{DEFAULT_HOST_IP}", "ignore" : ["SettingsProjectScope", "SettingsResourceScope"]}}""",
        SETTING_RPYC_PORT: f"""{{ "title" : "TCP Listen Port", "description" : "TCP port {SERVICE_NAME} should listen", "type" : "number", "minValue": 1, "maxValue": 65535,  "default" : {DEFAULT_HOST_PORT}, "ignore" : ["SettingsProjectScope", "SettingsResourceScope"]}}""",
        SETTING_RPYC_TIMEOUT: f"""{{ "title" : "Request Timeout (seconds)", "description" : "Timeout for synchronous RPyC requests in seconds", "type" : "number", "minValue": 30, "maxValue": 86400,  "default" : {DEFAULT_TIMEOUT}, "ignore" : ["SettingsProjectScope", "SettingsResourceScope"]}}""",
    }

    settings = binaryninja.Settings()
    if not settings.register_group(SERVICE_NAME, SERVICE_NAME):
        raise RuntimeWarning("Failed to register group setting")

    for name, value in all_settings.items():
        if not settings.register_setting(f"{SERVICE_NAME}.{name}", value):
            raise RuntimeWarning(f"Failed to register setting {name}")


class BinjaRpycService(rpyc.Service):
    ALIASES = [
        "binja",
    ]

    def __init__(self, bv):
        self.bv = bv
        return

    def on_connect(self, conn: rpyc.core.protocol.Connection):
        info(f"connect open: {conn}")
        return

    def on_disconnect(self, conn: rpyc.core.protocol.Connection):
        info(f"connection closed: {conn}")
        return

    exposed_binaryninja = binaryninja

    def exposed_bv(self):
        return self.bv

    def exposed_eval(self, cmd):
        return eval(cmd)
    
    def exposed_exec(self, cmd):
        return exec(cmd)

    def exposed_import_module(self, mod):
        return importlib.import_module(mod)

    def exposed_add_to_syspath(self, path):
        return sys.path.append(path)

    # - utilities

    # source: Union[str, bytes, bytearray, 'databuffer.DataBuffer', 'os.PathLike', 'BinaryView', 'project.ProjectFile'], update_analysis: bool = True,
    #     progress_func: Optional[ProgressFuncType] = None, options: Mapping[str, Any] = {}
    def exposed_binaryview_load(
        self,
        source: Any,
        update_analysis: bool = True,
        options_json: Optional[str] = None,
    ) -> Any:
        # wrap options dict
        options = {}
        if options_json is not None:
            options = json.loads(options_json)

        dbg(f"exposed_binaryview_load: source={source}, options={options}")

        # bv = binaryninja.BinaryView.load(
        bv = binaryninja.load(
            source,
            update_analysis=update_analysis,
            options=options,
        )
        dbg(f"exposed_binaryview_load: loaded bv={bv}")

        return bv


def is_service_started():
    global G_SERVICETHREAD
    # dbg(f"is_service_started: checking g_servicethread={G_SERVICETHREAD}")
    return G_SERVICETHREAD is not None


def start_service(
    host: str, port: int, timeout: int, bv: binaryninja.binaryview.BinaryView
) -> None:
    global G_SERVER, __bv
    G_SERVER = None
    __bv = bv

    for i in range(1):
        p: int = port + i
        try:
            service = rpyc.utils.helpers.classpartial(BinjaRpycService, bv)

            G_SERVER = rpyc.utils.server.ThreadedServer(
                service(),
                hostname=host,
                port=p,
                protocol_config={
                    "allow_public_attrs": True,
                    "allow_all_attrs": True,
                    "allow_getattr": True,
                    "allow_setattr": True,
                    "allow_delattr": True,
                    "allow_pickle": True,
                    "sync_request_timeout": timeout,
                },
            )
            break
        except OSError as e:
            err(f"OSError: {str(e)}")
            G_SERVER = None

    if not G_SERVER:
        err("failed to start server!")
        return

    info("server successfully started")
    G_SERVER.start()
    return


def rpyc_start(bv: Optional[binaryninja.binaryview.BinaryView] = None) -> None:
    global G_SERVICETHREAD
    dbg("Starting background service...")
    settings = binaryninja.Settings()
    host: str = settings.get_string(f"{SERVICE_NAME}.{SETTING_RPYC_HOST}")
    port: int = settings.get_integer(f"{SERVICE_NAME}.{SETTING_RPYC_PORT}")
    timeout: int = settings.get_integer(f"{SERVICE_NAME}.{SETTING_RPYC_TIMEOUT}")

    G_SERVICETHREAD = threading.Thread(
        target=start_service, args=(host, port, timeout, bv)
    )
    G_SERVICETHREAD.daemon = True
    G_SERVICETHREAD.start()
    info(f"{SERVICE_NAME} successfully started in background")
    # binaryninja.show_message_box(
    #     SERVICE_NAME,
    #     "Service successfully started, you can use any RPyC client to connect to this instance of Binary Ninja",
    #     binaryninja.MessageBoxButtonSet.OKButtonSet,
    #     binaryninja.MessageBoxIcon.InformationIcon,
    # )
    return


def shutdown_service() -> bool:
    if G_SERVER is None:
        err("Server is not running (Service not started?)")
        return False

    try:
        dbg("Shutting down service")
        G_SERVER.close()
        info("Service successfully shutdown")
    except Exception as e:
        err(f"Exception: {str(e)}")
        return False
    return True


def stop_service() -> bool:
    """Stopping the service"""
    global G_SERVICETHREAD
    if G_SERVICETHREAD is None:
        err("Thread is None (Service not started?)")
        return False

    dbg("Stopping service thread")
    if shutdown_service():
        G_SERVICETHREAD.join()
        G_SERVICETHREAD = None
        info("Service thread stopped")
    else:
        err("Error while shutting down service")
        return False
    return True


def rpyc_stop(bv: binaryninja.BinaryView):
    "Stopping background service..."
    if not stop_service():
        # binaryninja.show_message_box(
        #     SERVICE_NAME,
        #     "Service successfully stopped",
        #     binaryninja.MessageBoxButtonSet.OKButtonSet,
        #     binaryninja.MessageBoxIcon.InformationIcon,
        # )
        # else:
        binaryninja.show_message_box(
            SERVICE_NAME,
            "An error occured while stopping the service, check logs",
            binaryninja.MessageBoxButtonSet.OKButtonSet,
            binaryninja.MessageBoxIcon.ErrorIcon,
        )

    return
