from Api.Commands import Commands
from Api.IMAGE import ApiImageActivateCfm, ApiImageInfoCfm
from Api.PROD import ApiProdTestCfm
from termcolor import colored
from Api.PPGENERAL import ApiPpGetFwVersionCfm
from Api.FPGENERAL import ApiFpGetFwVersionCfm
from enum import Enum
from Api.PROD import DectMode
from Api.PPMM import (
    ApiPpMmFpNameInd,
    ApiPpMmRegistrationSearchInd,
    ApiPpMmRegistrationFailedInd,
    ApiPpMmRejectReason,
    ApiPpMmLockedInd,
    ApiPpMmRegistrationCompleteInd,
    ApiPpMmUnlockedInd,
)
from util import hexdump


def dectMode(mode_id: int):
    dect_mode = ""
    match DectMode(mode_id):
        case DectMode.EU:
            dect_mode = "EU"
        case DectMode.US:
            dect_mode = "US"
        case DectMode.SA:
            dect_mode = "SA"
        case DectMode.Taiwan:
            dect_mode = "Taiwan"
        case DectMode.Malaysia:
            dect_mode = "Malaysia"
        case DectMode.China:
            dect_mode = "China"
        case DectMode.Thailand:
            dect_mode = "Thailand"
        case DectMode.Brazil:
            dect_mode = "Brazil"
        case DectMode.US_Extended:
            dect_mode = "US Extended"
        case DectMode.Korea:
            dect_mode = "Korea"
        case DectMode.Japan_2ch:
            dect_mode = "Japan (2ch)"
        case DectMode.Japan_5ch:
            dect_mode = "Japan (5ch)"
        case _:
            dect_mode = "Invalid"
    return dect_mode


def parseMail(primitive, params):
    payload = bytes([primitive & 0xFF, primitive >> 8, *params])
    print(colored(f"{Commands(primitive).name} received", "blue"))
    match primitive:
        case Commands.API_FP_RESET_IND:
            print(
                "Success" if params[0] == 0 else f"Error: {params[0]}",
            )
        case Commands.API_PP_GET_FW_VERSION_CFM:
            return ApiPpGetFwVersionCfm.from_bytes(payload)
        case Commands.API_FP_GET_FW_VERSION_CFM:
            return ApiFpGetFwVersionCfm.from_bytes(payload)
        case Commands.API_FP_MM_GET_ID_CFM:
            print(f"ID: {params[1]:02x}{params[2]:02x}{params[3]:02x}{params[4]:02x}")
        case Commands.API_FP_MM_GET_ACCESS_CODE_CFM:
            access_code = (
                f"{params[1]:02x}{params[2]:02x}{params[3]:02x}{params[4]:02x}"
            )
            access_code = access_code.lstrip("f")
            print(f"Access Code: {access_code}")
        case Commands.API_FP_MM_SET_REGISTRATION_MODE_CFM:
            print(
                "Success" if params[0] == 0 else f"Error: {params[0]}",
            )
        case Commands.API_FP_MM_REGISTRATION_COMPLETE_IND:
            print("Registration complete!")
            print("Handset ID", params[1])
            # print(f"resp len {params[2]:02x} {params[3]:02x}")
            # length = int(params[2:3])
            # print("InfoElement", params[4 : 4 + length])
        case Commands.API_FP_MM_HANDSET_PRESENT_IND:
            print("New handset present!")
            print("Handset ID", params[0])
        case Commands.API_PP_MM_FP_NAME_IND:
            if len(params) == 1:
                return ApiPpMmFpNameInd("")
            return ApiPpMmFpNameInd.from_bytes(payload)
        case Commands.API_PP_MM_REGISTRATION_SEARCH_IND:
            print(hexdump(payload))
            ind = ApiPpMmRegistrationSearchInd.from_bytes(payload)
            return ind
        case Commands.API_PROD_TEST_REQ:
            print(f"OpCode: {params[1]:02x} {params[0]:02x}")
        case Commands.API_PROD_TEST_CFM:
            print(f"OpCode: {params[1]:02x} {params[0]:02x}")
            cfm = ApiProdTestCfm.from_bytes(payload)
            print("Opcode", cfm.Opcode)
            print("Param Length=", cfm.ParameterLength)
            print("Parameters=", cfm.getParameters())
            return cfm
        case Commands.API_IMAGE_ACTIVATE_CFM:
            print(
                "Success" if params[0] == 0 else f"Error: {params[0]}",
            )
        case Commands.API_PP_MM_REGISTRATION_FAILED_IND:
            return ApiPpMmRegistrationFailedInd.from_bytes(payload)
        case Commands.API_PP_MM_REGISTRATION_COMPLETE_IND:
            return ApiPpMmRegistrationCompleteInd.from_bytes(payload)
        case Commands.API_HAL_LED_CFM:
            print("LEDs toggled.")
        case Commands.API_IMAGE_ACTIVATE_CFM:
            print(ApiImageActivateCfm.from_bytes(payload).Status)
        case Commands.API_PP_MM_LOCKED_IND:
            return ApiPpMmLockedInd.from_bytes(payload)
        case Commands.API_PP_MM_UNLOCKED_IND:
            return ApiPpMmUnlockedInd.from_bytes(payload)
        case Commands.API_IMAGE_INFO_CFM:
            try:
                cfm = ApiImageInfoCfm.from_bytes(payload)
                print("Status", cfm.Status)
                print("ImageIndex", cfm.ImageIndex)
                print("ImageId", cfm.ImageId)
                print("DeviceId", cfm.DeviceId)
                print("LinkDate", cfm.LinkDate)
                print("NameLength", cfm.NameLength)
                print("LabelLength", cfm.LabelLength)
                print("Data", cfm.Data.decode("utf-8"))
            except Exception:
                pass

        case Commands.RTX_EAP_TARGET_RESET_IND:
            print("RTX_EAP_TARGET_RESET_IND recieved")
            print("=================================")
            print("TARGET RESET")
            print("=================================")

        case _:
            print(
                colored("Unknown primitive: ", "blue"),
                colored(Commands(primitive).name, "blue"),
            )
            return
