import asyncio
from MailProtocol import MailProtocol
import serial_asyncio
from Api.HAL import (
    ApiHalLedReqType,
    ApiHalLedCmdType,
    ApiHalLedCmdIdType,
    ApiHalWriteReq,
    HalAreaType,
)
from Api.FPGENERAL import ApiFpGetFwVersionReq
from Api.PPGENERAL import ApiPpGetFwVersionReq, ApiPpResetReq
from Api.IMAGE import ApiImageActivateReq, ApiImageInfoReq, ApiImageInfoCfm
from Api.PROD import ApiProdTestReq, DectMode
from Api.PPMM import (
    ApiPpMmRegistrationAutoReq,
    ApiPpMmRegistrationSearchReq,
    ApiMmSearchModeType,
    ApiPpMmRegistrationSelectedReq,
    ApiPpMmLockedReq,
    ApiPpMmLockedInd,
    ApiPpMmRejectReason,
    ApiPpMmLockReq,
    ApiPpMmUnlockedInd,
    ApiPpMmRegistrationSearchInd,
)
from Api.Commands import PtCommand, Commands
from Api.FPMM import ApiFpMmGetIdReq, ApiFpMmGetAccessCodeReq
from util import hexdump
from termcolor import colored
from Dect import DECT
import sys
from Api.Api import RsStatusType
from APIParser import dectMode


async def ensure_pp_mode(dct: DECT):
    print(colored("Sending 'API_PP_GET_FW_VERSION' request command...", "yellow"))
    pp_version = await dct.command(ApiPpGetFwVersionReq(), max_retries=2)

    if not pp_version:
        print(colored("Sending 'API_FP_GET_FW_VERSION' request command...", "yellow"))
        fp_version = await dct.command(ApiFpGetFwVersionReq(), max_retries=1)

        # Check if the DECT Chip is in FP or PP mode
        if fp_version:
            print(colored("DECT Chip is in FP mode, switching to PP mode", "yellow"))

            # Only needed if the image is offline (status = 0x1c / 28)
            print(
                colored("Sending 'API_IMAGE_ACTIVATE_REQ' request command...", "yellow")
            )
            await dct.command(ApiImageActivateReq(0x00, False))
            await asyncio.sleep(12)
        else:
            print(colored("DECT Chip is in unknown mode", "yellow"))
            sys.exit(1)
    else:
        print(colored("DECT Chip is in PP mode", "yellow"))
        print(colored("PP Version:", "yellow"), pp_version)


async def set_dect_mode(dct: DECT):
    print(
        colored(
            "Requesting Dect mode (API_PROD_TEST_REQ :: PT_CMD_GET_DECT_MODE)", "yellow"
        )
    )
    prod = await dct.command(
        ApiProdTestReq(opcode=PtCommand.PT_CMD_GET_DECT_MODE, data=[0x00])
    )
    dect_mode = prod.getParameters()[0]

    print(colored(f"DECT Mode: {dectMode(dect_mode)} {hex(dect_mode)}", "yellow"))
    if dect_mode != DectMode.EU:
        print(colored("DECT Mode is not EU, Setting now...", "yellow"))
        print(colored("Sending API_HAL_WRITE_REQ to write NVS", "yellow"))
        await dct.command(
            ApiHalWriteReq(HalAreaType.AHA_NVS, 0x05, bytes([0x25])),
        )
        print(colored("Sending API_PROD_TEST_REQ :: PT_CMD_SET_DECT_MODE", "yellow"))
        await dct.command(
            ApiProdTestReq(opcode=PtCommand.PT_CMD_SET_DECT_MODE, data=[0x00]),
        )

        prod = await dct.command(
            ApiProdTestReq(opcode=PtCommand.PT_CMD_GET_DECT_MODE, data=[0x00])
        )
        dect_mode = prod.getParameters()[0]
        print("DECT Mode after setting:", dectMode(dect_mode))
        if dect_mode != DectMode.EU:
            print(colored("Failed to set DECT Mode to EU", "red"))
            sys.exit(1)


async def get_locked_status(dct: DECT):
    print(colored("Sending 'API_PP_MM_LOCKED_REQ' request command...", "yellow"))
    await dct.command(ApiPpMmLockedReq(), timeout=0, max_retries=1)
    locked_resp = await dct.wait_for(
        [
            Commands.API_PP_MM_LOCKED_IND,
            Commands.API_PP_MM_UNLOCKED_IND,
        ],
        timeout=30,
    )
    if not locked_resp:
        print(colored("PPMM locking status failed", "red"))
        sys.exit(1)
    if type(locked_resp) is ApiPpMmLockedInd:
        print(colored("PPMM is locked", "blue"))
    else:
        print(colored("PPMM is unlocked", "blue"))


async def list_images(dct: DECT):
    i = 0
    images = []
    while True:
        print(colored(f"Getting info for image = {i}", "yellow"))
        image_info: ApiImageInfoCfm = await dct.command(ApiImageInfoReq(image=i))
        if not image_info:
            break

        status = RsStatusType(image_info.Status)
        if status == RsStatusType.RSS_NOT_FOUND or image_info.ImageIndex == 0xFF:
            print(colored(f"Stopping Enumeration after {i} images", "yellow"))
            break

        if status == RsStatusType.RSS_NO_DATA:
            print(colored(f"Skipping image {i} due to no data", "yellow"))
            i += 1
            continue

        image = image_info.to_dict()
        images.append(
            {
                "index": i,
                "status": status.name,
                "id": image.get("ImageId"),
                "device_id": image.get("DeviceId"),
                "link_date": image.get("LinkDate"),
                "name": image.get("name"),
                "label": image.get("label"),
            }
        )
        i += 1

    for image in images:
        color = "green" if image["status"] == "RSS_SUCCESS" else "magenta"
        print(colored(f"Image {image['index']}:", color))
        print(colored(f"Status: {image['status']}", color))
        print(colored(f"ID: {image['id']}", color))
        print(colored(f"Device ID: {image['device_id']}", color))
        print(colored(f"Link Date: {image['link_date']}", color))
        print(colored(f"Name: {image['name']}", color))
        print(colored(f"Label: {image['label']}", color))


async def open_line(dct: DECT):
    pass


async def main():
    port = "/dev/ttyUSB0"
    baudrate = 115200

    dct = DECT(port, baudrate)

    await dct.connect()

    # Uncomment to reset the DECT modules NV storage
    # await dct.command(ApiProdTestReq(opcode=PtCommand.PT_CMD_NVS_DEFAULT, data=[0x01]))

    await ensure_pp_mode(dct)
    await set_dect_mode(dct)
    await get_locked_status(dct)
    await list_images(dct)

    # print(colored("Trying easy pairing", "green"))
    # await dct.command(ApiPpMmEasyPairingSearchReq(), max_retries=1, timeout=30)
    auto_registration = False
    if auto_registration:
        print(colored("Trying auto registration", "green"))

        await dct.command(
            ApiPpMmRegistrationAutoReq(1, bytes([0xFF, 0xFF, 0x00, 0x00])),
            max_retries=1,
            timeout=0,
        )
    else:
        print(colored("Trying manual registration", "yellow"))
        print(
            colored(
                "Sending 'API_PP_MM_REGISTRATION_SEARCH_REQ' request command...",
                "yellow",
            )
        )
        await dct.command(
            ApiPpMmRegistrationSearchReq(0),
            max_retries=1,
            timeout=0,
        )

        baseStation = await dct.wait_for(
            Commands.API_PP_MM_REGISTRATION_SEARCH_IND, timeout=40
        )

        if not baseStation:
            print(colored("Base Station not found!", "red"))
            sys.exit(1)
        print(colored("Base Station found!", "green"))
        print(baseStation.caps())
        rfpi = baseStation.Rfpi
        print(colored("RFPI:", "yellow"), hexdump(bytes(rfpi), False))

        print(colored("Connecting to base station", "yellow"))
        await dct.command(
            ApiPpMmRegistrationSelectedReq(
                subscription_no=1,
                ac_code=bytes([0xFF, 0xFF, 0x00, 0x00]),
                rfpi=rfpi,
            ),
            max_retries=1,
            timeout=0,
        )

    status = await dct.wait_for(
        [
            Commands.API_PP_MM_REGISTRATION_COMPLETE_IND,
            Commands.API_PP_MM_REGISTRATION_FAILED_IND,
        ],
        timeout=40,
    )
    if not status:
        print(colored("Registration status not received!", "red"))
    else:

        if status.Primitive == Commands.API_PP_MM_REGISTRATION_COMPLETE_IND:
            print(colored("Registration complete!", "green"))
        elif status.Primitive == Commands.API_PP_MM_REGISTRATION_FAILED_IND:
            print(colored("Registration failed!", "red"))
            print(
                colored("Reason: ", "red"),
                colored(ApiPpMmRejectReason(status.Reason).name, "red"),
            )
        elif status.Primitive == Commands.API_PP_MM_REGISTRATION_SEARCH_IND:
            print(colored("Found a base station after auto", "yellow"))
            print(status.caps())

            await dct.command(
                ApiPpMmRegistrationSelectedReq(
                    subscription_no=1,
                    ac_code=bytes([0xFF, 0xFF, 0x00, 0x00]),
                    rfpi=status.Rfpi,
                ),
                max_retries=1,
                timeout=0,
            )

    await asyncio.Future()


if __name__ == "__main__":

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgram terminated.")
