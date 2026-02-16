#
# File: pytc.py
#
# Description: Module for command line interface interaction with PTC Integrity Manager.
#
#
# Author: Jamie, Last Edit: July 2025
#
# Prerequisites: PTC Integrity Manager 10 in path
#                Python 3.5 or higher
#

import sys
import subprocess
import re
from enum import Enum, auto
from typing import List

_im_cmd = "im"
_im_path_valid = None
_im_cmd_timeout_sec = 15


# The field strings must be PTC "fields" not the 'Display Name' of the field
# Can check via CLI with: im fields --fields=name,displayName --fieldsDelim=", "
# Note: Not a full enumeration of all PTC options, add as needed
class ItemFields(Enum):
    contains = "Contains"
    contained_by = "Contained By"
    category = "Category"
    satisfies = "Satisfies"
    satisfies_for_reports_only = "Satisfies for Reports only"
    implements = "Implements"
    implements_for_reports_only = "Implements for Reports only"
    implemented_by = "Is Implemented By"
    implemented_by_for_reports_only = "Is Implemented by for Reports only"
    shares = "Shares"
    shared_by = "Shared By"
    id = "ID"
    root_id = "Root ID"
    document_id = "Document ID"
    type = "Type"
    title = "Document Short Title"
    val_ver_procedure = "Is Verified By"  # Display Name 'Val/Ver By'
    is_verified_by_for_reports_only = "Is Verified by for Reports only"
    decomposed_from = "Decomposed From"
    decomposes_to = "Decomposes To"
    val_ver_responsible = "Verification Method"  # Display name is 'Val/Ver Responsible'
    results = "Result"  # Display Name 'Results'
    priority = "Priority"
    description = "Description"
    summary = "Summary"
    trace_status = "Trace Status"
    suspect_count = "Suspect Count"
    text = "Text"
    notes = "Notes"
    acceptance_criteria = "Acceptance Criteria"
    parameter_values = "Parameter Values"
    reference_mode = "Reference Mode"
    regulatory_submittal = "Regulatory Submittal"
    sod_configuration = "SOD Configuration"
    devices = "KARL STORZ Devices"
    source = "Source"
    sys_eng_notes = "Sys Eng Release Notes"
    sys_eng_notes_2 = "Sys Eng Notes 2"
    sys_eng_notes_3 = "Sys Eng Notes 3"
    baseline = "Baselinelabel"
    state = "State"
    is_positively_related_to = "Is Related To"
    is_negatively_related_to = "Is Related To'"
    project = "Project"


# Note: Not a full enumeration of all PTC options, add as needed
TraceFields = [ItemFields.implements,
               ItemFields.implements_for_reports_only,
               ItemFields.implemented_by,
               ItemFields.implemented_by_for_reports_only,
               ItemFields.shared_by,
               ItemFields.val_ver_procedure,
               ItemFields.is_verified_by_for_reports_only]

ExportedTextFields = [ItemFields.summary,
                      ItemFields.text,
                      ItemFields.acceptance_criteria,
                      ItemFields.notes,
                      ItemFields.results]


# Note: Not a full enumeration of all PTC options, add as needed
class Category(Enum):
    user_need = "User - Need"
    # new add
    stakeholder_req = "Stakeholder Requirement"
    functional = "Functional"
    standards = "Standards"
    comment_always_exported = "Comment -- Always Exported"
    ra_measure = "RA Measure"
    user_interface = "User Interface"
    performance = "Performance"
    security = "Security"
    comment = "Comment"
    future = "Future Requirement"
    pointer = "Pointer Requirement"
    specification = "Specification"
    heading = "Heading"
    doc_header = "Comment -- Document Header"


# Note: Not a full enumeration of all PTC options, add as needed
class DocType(Enum):
    feature_doc = "Feature Document"
    req_doc = "Requirement Document"
    spec_doc = "Specification Document"
    test_suite = "Test Suite"
    test_plan_doc = "Test Plan Document"


# Note: Not a full enumeration of all PTC options, add as needed
class ItemType(Enum):
    bug = "Bug"
    feat_req = "Feature Request"
    doc_task = "Documentation Task"
    imp_task = "Implementation Task"
    personal_task = "Personal Task"
    release = "Release"
    feat_flag = "Feature Flag"
    mks_issue = "MKS Issue"
    req = "Requirement"


# TODO: Missing all 'related' traces
class TraceType(Enum):
    downstream_suspect = "downstream_suspect"
    downstream = "downstream"
    none = "none"
    upstream_downstream = "upstream downstream"
    upstream_downstream_suspect = "upstream downstream suspect"
    upstream_suspect_downstream_suspect = "upstream suspect downstream suspect"
    upstream_suspect_downstream = "upstream suspect downstream"
    upstream_suspect = "upstream suspect"
    upstream = "upstream"


class RefMode(Enum):
    share = "Share"
    author = "Author"
    reuse = "Reuse"


class ReferenceMode(Enum):
    copy = "copy"
    reuse = "reuse"
    share = "share"


SuspectTraceSet = [TraceType.downstream_suspect,
                   TraceType.upstream_downstream_suspect,
                   TraceType.upstream_suspect_downstream_suspect,
                   TraceType.upstream_suspect_downstream,
                   TraceType.upstream_suspect]

NoSuspectTraceSet = [TraceType.downstream,
                     TraceType.none,
                     TraceType.upstream_downstream,
                     TraceType.upstream]

CategorySet = List[Category]

subproc_count = 0


def subproc_debug(cmd_str: str, stdout=None, stderr=None):
    global subproc_count
    subproc_count += 1
    try:
        return subprocess.run(cmd_str, timeout=_im_cmd_timeout_sec, stdout=stdout, stderr=stderr)
    except subprocess.TimeoutExpired:
        print("Operation Timeout: " + cmd_str)
        raise TimeoutError


# Do not directly set _im_path, done through helper method to only call PTC CMD once per setting of path
def set_im_path(path: str) -> bool:
    global _im_cmd
    global _im_path_valid
    _im_cmd = path
    _im_path_valid = None
    _im_path_valid = ptc_in_path()
    return _im_path_valid


def ptc_in_path() -> bool:
    global _im_path_valid
    if _im_path_valid is None:
        try:
            out = subproc_debug(_im_cmd + " about", stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            _im_path_valid = (out.returncode == 0)
        except FileNotFoundError as e:
            print("Invalid PTC path: " + _im_cmd)
            _im_path_valid = False
    return _im_path_valid


def valid_field(field_name) -> bool:
    if isinstance(field_name, ItemFields):
        field_name = field_name.value
    cmd_args = "viewfield \"" + str(field_name) + "\""
    im_out = subproc_debug(_im_cmd + ' ' + cmd_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return im_out.returncode == 0


# Assumes field name is valid
def is_int_field(field_name) -> bool:
    if isinstance(field_name, ItemFields):
        field_name = field_name.value
    cmd_args = "viewfield \"" + str(field_name) + "\""
    im_out = subproc_debug(_im_cmd + ' ' + cmd_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if re.search('Type: integer', im_out.stdout.decode('latin-1')):
        return True
    else:
        return False


def is_rich_field(field_name) -> bool:
    if isinstance(field_name, ItemFields):
        field_name = field_name.value
    cmd_args = "viewfield \"" + str(field_name) + "\""
    im_out = subproc_debug(_im_cmd + ' ' + cmd_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if re.search('Type: fva', im_out.stdout.decode('latin-1')):
        return True
    else:
        return False


class Item:
    RichTextField = ":80:rich"

    # Since you cannot create a 'copy' with new root ID through the CLI, blank items need to be created then
    # all the items copied over manually. This list contains all the items that will be copied over.
    # Tuples of (ItemFields, bool)
    CopyFields = \
        [(ItemFields.category, False),
         (ItemFields.summary, False),
         (ItemFields.text, True),
         (ItemFields.notes, True),
         (ItemFields.results, False),
         (ItemFields.priority, False),
         (ItemFields.acceptance_criteria, True),
         (ItemFields.regulatory_submittal, False),
         (ItemFields.sod_configuration, False),
         (ItemFields.devices, False),
         (ItemFields.source, False),
         (ItemFields.sys_eng_notes, False),
         (ItemFields.sys_eng_notes_2, False),
         (ItemFields.sys_eng_notes_3, False),
         (ItemFields.satisfies, False),
         (ItemFields.satisfies_for_reports_only, False),
         (ItemFields.implements, False),
         (ItemFields.implements_for_reports_only, False),
         (ItemFields.implemented_by, False),
         (ItemFields.implemented_by_for_reports_only, False),
         (ItemFields.val_ver_procedure, False),
         (ItemFields.is_verified_by_for_reports_only, False)]

    def __init__(self, ptc_id: int, init_type: bool = False) -> object:
        self.ptc_id = ptc_id
        # print("Item.__init__(): id=" + str(self.ptc_id))
        self.type = None
        self.fields_cache = {}

        if not ptc_in_path():
            print("PTC not found in path")
        else:
            if init_type:
                self.type = self.get_field(ItemFields.type)

    def get_branches(self):
        cmd_args = "viewissue --showBranches " + str(self.ptc_id)
        im_out = subproc_debug(_im_cmd + ' ' + cmd_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output_text = im_out.stdout.decode('latin-1')
        # print("get_branches(): command='" + _im_cmd + " " + cmd_args + "'; output='" + output_text + "'")
        match = re.findall("(?<=Branch )\d{1,7}(?= based on time)", output_text)
        return match

    def get_parent(self):
        cmd_args = "viewissue --showBranches " + str(self.ptc_id)
        im_out = subproc_debug(_im_cmd + ' ' + cmd_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        match = re.search("(?<=Parent: Issue )\d{1,7}(?= based on time)", im_out.stdout.decode('latin-1'))
        if match:
            return match.group(0)
        return None

    def get_field(self, field_name, field_args: str = "") -> str:
        if isinstance(field_name, ItemFields):
            field_name = field_name.value

        cache_name = field_name + field_args
        if cache_name not in self.fields_cache:
            cmd_args = "issues --fields=\"" + str(field_name) + "\"" + field_args + " " + str(self.ptc_id)
            im_out = subproc_debug(_im_cmd + ' ' + cmd_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output_text = im_out.stdout.decode('latin-1')
            # print("get_field(): command='" + _im_cmd + " " + cmd_args + "'; output='" + output_text + "'")
            if re.search('Field .* does not exist', im_out.stderr.decode('latin-1')):
                raise NameError
            elif re.search('Item .* does not exist', im_out.stderr.decode('latin-1')):
                raise ValueError
            self.fields_cache[cache_name] = output_text.rstrip()
        return self.fields_cache[cache_name]

    # regex_search only applicable when field val is a single string
    def is_field(self, field_name, field_val, regex_match: bool = None) -> bool:
        item_data = self.get_field(field_name)
        # None for field_val is non empty check
        if field_val is None:
            return len(item_data) != 0

        # field_val is a list
        elif type(field_val) is list:
            for cur_val in field_val:
                if isinstance(cur_val, Enum):
                    cur_val = cur_val.value
                if cur_val == item_data:
                    return True
            return False
        # field_val is singular
        else:
            if isinstance(field_val, Enum):
                field_val = field_val.value

            if regex_match is not None and isinstance(field_val, str):
                return regex_match == bool(re.search(field_val, item_data))
            else:
                try:
                    return item_data == str(field_val)
                except ValueError:
                    print("Unable to convert field_val to a string")
                    return False

    def set_field(self, field_name, field_val, rich_content: bool = False):
        # If the enum is used, get the associated string value
        if isinstance(field_name, ItemFields):
            field_name = field_name.value

        # If a list is passed in, convert it to a comma delimited string
        if isinstance(field_val, list):
            arg_str = ""
            for cur_val in field_val:
                if len(arg_str) > 0:
                    arg_str += ", "
                arg_str += str(cur_val)
            field_val = arg_str

        field_arg = "--richContentField" if rich_content else "--field"
        cmd_args = "editissue " + field_arg + "=\"" + str(field_name) + "\"=\"" + str(field_val) + "\" " + str(
            self.ptc_id)
        im_out = subproc_debug(_im_cmd + ' ' + cmd_args, stdout=sys.stdout, stderr=sys.stderr)
        return

    def remove_rich_text_color(self,
                               field: ItemFields = ItemFields.text,
                               foreground=True,
                               background=True):
        text = self.get_field(field, field_args=self.RichTextField)
        new_text = str(text)

        # TODO: Smarter parsing for matched sets to handle foreground and background independently
        if foreground:
            new_text = re.sub("<font color=\"#.*?\">|</font>", "", new_text)
            if re.search("<span .*?color:.*?\"", text):
                new_text = re.sub("<span .*?color:.*?\">|</span>", "", new_text)
        if background:
            new_text = re.sub("<span .*?background-color:.*?\">|</span>", "", new_text)

        if new_text != text:
            print("Orig text for " + field.value)
            print(text)
            print("New text for " + field.value)
            print(new_text)
            new_text = new_text.replace('\"', '\\\"')
            self.set_field(field, new_text, True)
        else:
            print("No colored text found in " + field.value)

    def get_relationship(self, rel_type, recursive=False, level=0) -> list:
        try:
            field_data = self.get_field(ItemFields(rel_type).value)
            # a, x, y, are appended to trace PTC ID to indicate the traces Relationship Flags
            rel_ids = field_data.strip('\n'). \
                replace('a', ''). \
                replace('y', ''). \
                replace('x', '') \
                .split(', ')

            # End of node case, return empty list
            if len(rel_ids) == 1 and not rel_ids[0]:
                return []

            rel_ids = list(map(int, rel_ids))  # convert from str to int
            if recursive:
                idx = 0
                # inserting child items in place to return items matching order
                while idx < len(rel_ids):
                    rid = rel_ids[idx]
                    next_level = level + 1
                    next_ids = Item(rid).get_relationship(rel_type, recursive, next_level)
                    idx += 1
                    # Insert in place to keep IDS in order they appear in a document
                    if len(next_ids) > 0:
                        rel_ids = rel_ids[:idx] + next_ids + rel_ids[idx:]
                        idx = idx + len(next_ids)
            return rel_ids
        except ValueError as e:
            print("get_relationship() type not found")

    def check_trace(self, item_field: ItemFields, valid_traces: CategorySet = []) -> bool:
        trace_ids = self.get_relationship(item_field)

        # Check traced items for specific types if specified
        if valid_traces is List and len(valid_traces) > 0:
            for trace_id in trace_ids:
                trace_item: Item = Item(trace_id)
                for valid_trace in valid_traces:
                    if trace_item.is_field(ItemFields.category, valid_trace):
                        return True
            # No traces found that met criteria specified
            return False
        # No types specified so just check that at least a trace exists
        else:
            if trace_ids is None:
                print("Warning: Unable to process item trace for PTC ID: " + str(self.ptc_id))
                return False
            else:
                return 0 < len(trace_ids)

    # Make function to create copy
    # Unspecified location will add item at same level directly below current item
    def create_copy(self, ref_mode: ReferenceMode, parent_id: int = None, insert_location: str = None) -> int:
        print("Creating copy of item: " + str(self.ptc_id))

        if not parent_id:
            my_id = self.get_field(ItemFields.contained_by)
            parent_id = int(my_id)

            insert_location = "after:" + str(self.ptc_id)

        print("\tInto Document: " + str(parent_id))

        if ref_mode.value == ReferenceMode.copy.value:
            print("Creating New Item!")
            cmd_args = "createcontent --type=Requirement --parentid=" + str(
                parent_id) + " --insertLocation=" + insert_location
            print(cmd_args)
            im_out = subproc_debug(_im_cmd + ' ' + cmd_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output = im_out.stderr.decode('latin-1').rstrip()
            print(output)
            # Get new item ID
            id_re = re.search("\d+", output)
            if not id_re:
                return 0

            new_id = id_re[0]
            new_item = Item(new_id)

            for cur_copy in self.CopyFields:
                field_args = self.RichTextField if cur_copy[1] else ""
                copy_data = self.get_field(cur_copy[0], field_args)
                if len(copy_data) > 0:
                    new_item.set_field(cur_copy[0], copy_data, cur_copy[1])

            return new_id

        elif isinstance(ref_mode, ReferenceMode):
            print("Creating " + ref_mode.value + " copy of item")

            cmd_args = "copycontent --parentid=" + str(parent_id) + " --refmode=" + ref_mode.value

            if insert_location:
                cmd_args += " --insertLocation=\"" + insert_location + "\""

            cmd_args += " " + str(self.ptc_id)
            print(cmd_args)
            im_out = subproc_debug(_im_cmd + ' ' + cmd_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output = im_out.stderr.decode('latin-1').rstrip()
            print(output)
            # Get new item ID
            id_re = re.findall("\d+", output)
            if not id_re:
                return 0

            return id_re[len(id_re) - 1]

        return 0

    def get_param(self, param: str) -> str:
        param_text = self.get_field(ItemFields.parameter_values)
        param_value = re.search("(?<=" + param + "=).*", param_text)
        if param_value:
            return param_value.group(0)
        return None

    def show_gui(self):
        subprocess.run([_im_cmd, "viewissue", "--gui", str(self.ptc_id)])

    # input for 'insert_loc'
    # 'first' inserts the content at the beginning of the list
    # 'last' inserts the content at the end of the list
    # 'before:name' inserts the content before the specified ID (name)
    # 'after:name' inserts the content after the specified ID (name)
    # [0,...] inserts the content at the specified location. If a negative is specified, the content is inserted at
    # the beginning of the list. If the number specified is too large, the content is inserted at the end of the list.
    def move_item(self, parent_id: int, insert_loc="last", with_recurse=False):
        recurse_args = ""
        if with_recurse:
            recurse_args = " --recurse"
        cmd_args = "movecontent --parentID=" + str(parent_id) + " --insertLocation=" + str(insert_loc) \
                   + recurse_args + " " + str(self.ptc_id)
        im_out = subproc_debug(_im_cmd + ' ' + cmd_args, stdout=sys.stdout, stderr=sys.stderr)
        return


class Document(Item):
    class TemplateItem(Enum):
        header = auto()
        signature_block = auto()
        id_block = auto()
        config_block = auto()
        history = auto()
        device_description = auto()
        references = auto()

    def __init__(self, ptc_id):
        Item.__init__(self, ptc_id, init_type=True)
        self.item_ids = []
        self.items_cache = {}

        # Check for document type
        try:
            DocType(self.type)  # is the type found in the DocType enum
        except ValueError as e:
            raise e

    # Get an item within the document, allows usage of item cache.
    def get_item(self, ptc_id: int) -> Item:
        if ptc_id not in self.items_cache:
            self.items_cache[ptc_id] = Item(ptc_id)
        return self.items_cache[ptc_id]

    # Get items contained by the document
    def get_item_ids(self):
        if len(self.item_ids) == 0:
            self.item_ids = self.get_relationship(ItemFields.contains, True)
        return self.item_ids

    # category - List of Requirement 'Category' values to perform checks
    # field: - Field to check
    # valid_values[optional] - Criteria for checking, valid input types:
    #              str - valid data string to compare against item data, can be regex
    #              list[str] - list of valid data strings to compare against
    #              Enum - string enum whose value is the valid data string used for comparison
    #              list[Enum] - list of string enums used to check for valid item data
    #              None - Check for non-empty field
    # trace_field[optional] - True if field is a trace type and field check is performed on category of trace items
    # regex_search[optional] - None for non-regex valid_values, for regex,
    #                          False for no regex match as compliant
    #                          True for matching the regex for compliance
    # print_status[optional] - True to print status of check
    def check_document_field(self, category: List[Category],
                             field: ItemFields,
                             valid_values=None,
                             trace_field=False,
                             regex_match=None,
                             print_status: bool = False) -> list:
        violating_ids = []
        for idx, doc_item_id in enumerate(self.get_item_ids()):

            # Get item will use cached copy if available
            doc_item = self.get_item(doc_item_id)

            if print_status:
                print("Item " + str(idx) + " of " + str(len(self.get_item_ids())) + "    ", end='\r', flush=True)

            if doc_item.is_field(ItemFields.category, category):
                if trace_field:
                    if not doc_item.check_trace(field, valid_values):
                        violating_ids.append(doc_item_id)
                else:
                    if not doc_item.is_field(field, valid_values, regex_match):
                        violating_ids.append(doc_item_id)
        return violating_ids

    # Helper routine to check text fields that are part of PTC export
    def check_document_fields(self, category: List[Category],
                              fields: List[ItemFields],
                              valid_values=None,
                              trace_field=False,
                              regex_match=None,
                              print_status: bool = False) -> list:
        violating_ids = []
        for field in fields:
            cur_ids = self.check_document_field(category, field, valid_values, trace_field, regex_match, print_status)

            violating_ids = list(set(violating_ids) | set(cur_ids))

        return violating_ids

    def get_template_item(self, template_item: TemplateItem):
        for doc_item_id in self.get_item_ids():

            # Get item will use cached copy if available
            doc_item = self.get_item(doc_item_id)

            if Category.comment_always_exported.value == doc_item.get_field(ItemFields.category):
                cur_text = doc_item.get_field(ItemFields.text)
                re_check = ""
                if template_item is self.TemplateItem.header:
                    re_check = "(SOD Product Specification\/SOD Produkt Spezifikation)|(Device Product Specification\/Produkt Spezifikation)|(SOD Specification\/SOD Spezifikation)"
                elif template_item is self.TemplateItem.id_block:
                    re_check = "(PTC ID Number)"
                    #re_check = "(?<=Number)\W*.*\W*(?=Name)"
                elif template_item is self.TemplateItem.config_block:
                    re_check = "(Device Configuration)"

                if re.search(re_check, cur_text):
                    return doc_item
        return None

    # Checks if the PTC document has the parameter 'repository' set to True
    def is_repo(self) -> bool:
        param_text = self.get_field(ItemFields.parameter_values)
        return bool(re.search("(?<=repository=)[T|t]rue", param_text))



