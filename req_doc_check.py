#!/usr/bin/env python3
#
# File: req_doc_check.py
#
# Description: Checks PTC Document to ensure SysE checklist items are fulfilled
# Last updated by: Jamie, July 2025
#
# Prerequisites: PTC Integrity Manager 10 in path
#                Python 3.5 or higher
#
##NOTE this version missing some checks

import sys
import os
import re
import argparse
from enum import Enum, auto
from typing import List
from datetime import datetime
import time
sys.path.insert(0, "..")
import pytc


# Must be in order of phases for comparator operators to work
class DocPhase(Enum):
    devel = auto()
    proto = auto()
    pilot = auto()
    production = auto()

    # >= operator
    def __ge__(self, other):
        return self.__get_idx__() >= other.__get_idx__()

    def __get_idx__(self):
        idx = 0
        for cur_val in DocPhase:
            if self == cur_val:
                return idx
            idx += 1


def to_doc_phase(string):
    try:
        if isinstance(string, str):
            string = string.lower()
        return DocPhase[string]
    except KeyError as e:
        msg = "Invalid document phase input \'%s\'" % str(e.args[0])
        raise argparse.ArgumentTypeError(msg)


class ReqDocType(Enum):
    dpsGRM = auto()
    sodpsGRM = auto()
    dps = auto()
    sodps = auto()
    detect = auto()


def to_doc_type(string):
    try:
        if isinstance(string, str):
            string = string.lower()
        return ReqDocType[string]
    except KeyError as e:
        msg = "Invalid document type input \'%s\'" % str(e.args[0])
        raise argparse.ArgumentTypeError(msg)


# Helper routine for printing status checks
def print_pass_fail(ptc_ids: List[int],
                    pass_str: str = "All items met criteria check.",
                    fail_str: str = "Following PTC IDs failed to meet criteria check;"):

    if sys.stdout.encoding == 'utf-16' or sys.stdout.encoding == 'utf-8':
        PASS_CHECK = u'\u2713'
        FAIL_MARK = u'\u20e0'
    else:
        PASS_CHECK = 'PASS'
        FAIL_MARK = 'FAIL'

    if len(ptc_ids) == 0:
        print(PASS_CHECK + " " + pass_str)
    else:
        print(FAIL_MARK + " " + fail_str + " " + str(ptc_ids))


if not ((sys.version_info[0] >= 3) and (sys.version_info[1] >= 5)):
    print("Requires Python version 3.5 or higher")
    exit(0)


def main():
    parser = argparse.ArgumentParser(description="Check PTC Requirements Documents for compliance to SysE checklist. Refer"
                                                 " to README for further information.")
    parser.add_argument('ptc_id', metavar='ID', type=int, nargs=1, help="PTC ID of requirements document")
    parser.add_argument('-p', '--phase', metavar='Phase', type=to_doc_phase, default="production",
                        help="Project phase for checks, options are; devel, proto, pilot, production")
    parser.add_argument('-t', '--type', metavar='Type', type=to_doc_type, default="detect",
                        help="Document type for checks, options are; dps, sodps, detect (determines document type from header)")
    parser.add_argument('-x', '--experimental', action='store_true',
                        help="Perform all experimental checks.")
    parser.add_argument('-s', '--status', action='store_true',
                        help="Show status of checks in progress.")
    parser.add_argument('-d', '--duration', action='store_true',
                        help="Print the duration of the document check process")
    args = parser.parse_args()

    if args.duration:
        start_time = time.time()

    try:
        req_doc = pytc.Document(args.ptc_id[0])
    except ValueError:
        print("Invalid PTC Document ID Provided: " + str(args.ptc_id[0]))
        exit(-1)

    # Display document information
    print((datetime.now().ctime()) + ", CheckScript v2.3")

    title = req_doc.get_field(pytc.ItemFields.title)
    print("Performing " + args.phase.name + " phase check on " + req_doc.type + " " + str(req_doc.ptc_id) + ", " + title, flush=True)

# Update Script number/versioning to reflect details of large changes
# v2.0 is reflecting the forReportsOnly comma space fix and pointing to fields ending in "for Reports only".
# v2.1 Minor update to correct DPS v SODPS use reference to know what to run when
# v2.2 added acceptance criteria check for N/A and/or Not Applicable
#v2.3 added check on preGRM templates for Source field.
    # Updated Header support and now checks for Project details for PTC ID and Sys/Dev Name instead of in signature block

    if args.status:
        print("Querying items (may take a couple minutes)... ", end='', flush=True)
        print(str(len(req_doc.get_item_ids())) + " items found")

    print("Header Details")
    # Check some specific information in the document headers
    # Assume first "Comment - Always Exported" is the header
    header_item = req_doc.get_template_item(pytc.Document.TemplateItem.header)

    if header_item:
        cur_text = header_item.get_field(pytc.ItemFields.text)
        sap = re.search("3[0]{5}\d{6}", cur_text)
        if sap:
            print("SAP ID: " + str(sap[0]))
        else:
            print("SAP ID not found in header")

        desc = re.search("(?<=Spezifikation)\W*.*\W*(?=Document)", cur_text)
        if desc:
            print("Project Name: " + str(desc[0]).strip())
        else:
            print("Project Name not found in header")

        if args.type is ReqDocType.detect:
            if re.match("SOD Product Specification/SOD Produkt Spezifikation GRM", cur_text):
                print("SODPS GRM Document Detected")
                args.type = ReqDocType.sodpsGRM
            elif re.match("Device Product Specification/Produkt Spezifikation GRM", cur_text):
                print("DPS GRM Document Detected")
                args.type = ReqDocType.dpsGRM
            elif re.match("SOD Specification", cur_text):
                print("SODPS Document Detected")
                args.type = ReqDocType.sodps
            elif re.match("SOD Product Specification", cur_text):
                print("SODPS Document Detected")
                args.type = ReqDocType.sodps
            elif re.match("Device Product Specification", cur_text):
                print("DPS Document Detected")
                args.type = ReqDocType.dps
            else:
                print("Warning: Unable to detect requirement document type")

    else:
        print("Unable to find header, check that Project or Product Name are not in header")


        # Device Product Specification/Produkt Spezifikation GRM
        # SOD Product Specification/SOD Produkt Spezifikation GRM
        # SOD Product Specification/SOD Produkt Spezifikation


    print("Signature Block Details")
    header_item = req_doc.get_template_item(pytc.Document.TemplateItem.signature_block)

    if header_item:
        cur_text = header_item.get_field(pytc.ItemFields.text)
        # Get PTC ID & PN from header
        #ptc_id = re.search("(?<=PTC:)\s*\d*", cur_text)
        #OLD VERSION -- ptc_id = re.search("(?<=PTC ID)\s*[\w, \/]*", cur_text)
        # ?<= negative lookbehind

       # if ptc_id:
       #     print("PTC ID:" + str(ptc_id[0]).strip())
       # else:
       #     print("PTC ID not found in signature block")

    # PTC found in exported document, not needed in check, unreliable.

        pn = re.search("(?<=PN:)\s*[\w, \/]*", cur_text)
        if pn:
            print("PN: " + str(pn[0]).strip())
        else:
            print("Part Number not found in signature block")
    else:
        print("Unable to find signature block")

    # List of category types to treat as functional requirements for field checking
    req_categories = [pytc.Category.functional,
                      pytc.Category.ra_measure,
                      pytc.Category.standards,
                      pytc.Category.pointer]

    req_categories_w_user_need = req_categories.copy()
    req_categories_w_user_need.append(pytc.Category.user_need)

    ########## Checks to start performing at development phase gate ##########
    if args.phase >= DocPhase.devel:
        # Checks SRD for traces from Stakeholder Requirements to Functional Requirements or Standards
        print("Checking Stakeholder Requirements to requirement traces...")
        ptc_ids = req_doc.check_document_field(category=pytc.Category.stakeholder_req,
                                               field=pytc.ItemFields.implemented_by_for_reports_only,
                                               valid_values=[pytc.Category.functional, pytc.Category.standards],
                                               trace_field=True,
                                               print_status=args.status)
        print_pass_fail(ptc_ids)

        # Checks SND for traces from Stakeholder Requirements to Functional Requirements or Standards
        print("Checking User Need to requirement traces...")
        ptc_ids = req_doc.check_document_field(category=pytc.Category.user_need,
                                               field=pytc.ItemFields.implemented_by_for_reports_only,
                                               valid_values=[pytc.Category.functional, pytc.Category.standards],
                                               trace_field=True,
                                               print_status=args.status)
        print_pass_fail(ptc_ids)

        #check is summary field populated
        print("Checking requirements and user needs for Summary field populated...")
        ptc_ids = req_doc.check_document_field(category=req_categories_w_user_need,
                                               field=pytc.ItemFields.summary,
                                               print_status=args.status)
        print_pass_fail(ptc_ids)

        # Priority check
        print("Checking requirements and user needs for Necessary Priority...")
        ptc_ids = req_doc.check_document_field(category=req_categories_w_user_need,
                                               field=pytc.ItemFields.priority,
                                               valid_values=["Necessary"],
                                               print_status=args.status)
        print_pass_fail(ptc_ids)

        # Results field populated
        print("Checking requirements and user needs for Results field populated...")
        ptc_ids = req_doc.check_document_field(category=req_categories_w_user_need,
                                               field=pytc.ItemFields.results,
                                               print_status=args.status)
        print_pass_fail(ptc_ids)

        # Check for suspect traces
        print("Checking requirements and user needs for suspect traces...")
        ptc_ids = req_doc.check_document_field(category=req_categories_w_user_need,
                                               field=pytc.ItemFields.suspect_count,
                                               valid_values=0,
                                               print_status=args.status)
        print_pass_fail(ptc_ids)

        # Check for "TBDs" or "TO DOs"
        print("Checking requirements and user needs for TBD and TODO...")
        ptc_ids = req_doc.check_document_fields(category=req_categories_w_user_need,
                                                fields=pytc.ExportedTextFields,
                                                valid_values="[Tt][Oo][Dd][Oo]|[Tt][Bb][Dd]",
                                                regex_match=False,  # Check to make sure items don't match the regex
                                                print_status=args.status)
        print_pass_fail(ptc_ids)

        # Check for "Not Applicable or N/A in Acceptance Criteria Category" |[Nn][Oo][Tt][Aa][Pp][Pp][Ll][Ii][Cc][Aa][Bb][Ll][Ee]
        print("Checking requirements and user needs for N/A and Not Applicable in Acceptance Criteria...")
        ptc_ids = req_doc.check_document_fields(category=req_categories_w_user_need,
                                                fields=pytc.ExportedTextFields,
                                                valid_values="[Nn][/][Aa]|[Nn][Oo][Tt] [Aa]pplicable",
                                                regex_match=False,  # Check to make sure items don't match the regex
                                                print_status=args.status)
        print_pass_fail(ptc_ids)


        # check for "shalls"
        print("Checking requirements \"Shall\" text...")
        ptc_ids = req_doc.check_document_field(category=req_categories,
                                               field=pytc.ItemFields.text,
                                               valid_values="[Ss]hal",
                                               regex_match=True,  # Check to make sure items match the regex
                                               print_status=args.status)
        print_pass_fail(ptc_ids)

        # RASS / Regulatory Submittal field populated
        print("Checking requirements for RASS / Regulatory Submittal field populated...")
        ptc_ids = req_doc.check_document_field(category=req_categories,
                                               field=pytc.ItemFields.regulatory_submittal,
                                               print_status=args.status)
        print_pass_fail(ptc_ids)


    #### Only checked for SOD ####
        if args.type is ReqDocType.sodps or ReqDocType.sodpsGRM:
            # Results field populated
            print("Checking requirements for SOD Config field populated...")
            ptc_ids = req_doc.check_document_field(category=req_categories,
                                                   field=pytc.ItemFields.sod_configuration,
                                                   print_status=args.status)
            print_pass_fail(ptc_ids)

    #### Only checked for PreGRM ####
        if args.type is ReqDocType.sodps or ReqDocType.dps:
            # Source field populated
            print("Checking PreGRM requirements for Source field populated...")
            ptc_ids = req_doc.check_document_field(category=req_categories,
                                                   field=pytc.ItemFields.source,
                                                   print_status=args.status)
            print_pass_fail(ptc_ids)

    ########## Checks to start performing at prototype phase gate ##########
    if args.phase >= DocPhase.proto:
        # Check document that all Functional Reqs have val/ver responsible
        print("Checking requirements and user needs for Val/Ver Responsible...")
        ptc_ids = req_doc.check_document_field(category=req_categories_w_user_need,
                                               field=pytc.ItemFields.val_ver_responsible,
                                               print_status=args.status)
        print_pass_fail(ptc_ids)

        # Check document that all Functional Reqs have val/ver procedure
        print("Checking requirements and user needs for Val/Ver Procedure...")
        ptc_ids = req_doc.check_document_field(category=req_categories_w_user_need,
                                               field=pytc.ItemFields.is_verified_by_for_reports_only,
                                               trace_field=True,
                                               print_status=args.status)
        print_pass_fail(ptc_ids)

        print("Checking exported comments for TBD and TODO...")
        ptc_ids = req_doc.check_document_field(category=pytc.Category.comment_always_exported,
                                               field=pytc.ItemFields.text,
                                               valid_values="[Tt][Oo][Dd][Oo]|[Tt][Bb][Dd]",
                                               regex_match=False,  # Check to make sure items don't match the regex
                                               print_status=args.status)
        print_pass_fail(ptc_ids)




    #### Experimental Checks ####
    if args.experimental:
        print("**** Experimental Checks ****")
        # Checking for colored text
        print("Checking requirements and user needs for any colored text...")
        ptc_ids = req_doc.check_document_field(category=req_categories_w_user_need,
                                               field=pytc.ItemFields.text.value + pytc.Item.RichTextField,  # Pass in field as string with flags to get rich text
                                               valid_values="(?<=color)(=\"|:)#(?!000000)[A-Fa-f0-9]{6}",
                                               regex_match=False,  # Check to make sure items match the regex
                                               print_status=args.status)
        print_pass_fail(ptc_ids)




    if args.duration:
        elapsed_time = time.time() - start_time
        print(time.strftime("Check performed in: %H:%M:%S", time.gmtime(elapsed_time)))

    print("Done")


if __name__ == '__main__':
    try:
        main()
    except TimeoutError:
        print("PTC Not responding, please ensure you are logged in and connected to PTC.")
        sys.exit(-1)
