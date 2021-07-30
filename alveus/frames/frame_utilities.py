import os
import wx

from _ids import *
from frames.auxiliary_frames import DeleteItemDialog, DeleteItemsDialog, MoveFolderDialog


# -------------------------------------------------------------------------------------------------------------------- #

def GetFilePath(parent, message='Open', defaultDir=os.getcwd(), defaultFile='', wildcard=''):
    dlg = wx.FileDialog(parent, message=message, defaultDir=defaultDir, defaultFile=defaultFile,
                        wildcard=wildcard,
                        style=wx.FD_OPEN | wx.FD_MULTIPLE | wx.FD_CHANGE_DIR)

    if dlg.ShowModal() == wx.ID_OK:
        path = dlg.GetPaths()[0]
    else:
        path = None

    dlg.Destroy()

    return path


# -------------------------------------------------------------------------------------------------------------------- #

def GetDirPath(parent, message='Open', defaultPath=os.getcwd()):
    dlg = wx.DirDialog(parent, message=message, defaultPath=defaultPath, style=wx.DD_DEFAULT_STYLE | wx.DD_CHANGE_DIR)

    if dlg.ShowModal() == wx.ID_OK:
        path = dlg.GetPath()
    else:
        path = None

    dlg.Destroy()

    return path


# -------------------------------------------------------------------------------------------------------------------- #

def DeleteSingleTreeItem(parent, item, method, *args):

    dlg = DeleteItemDialog(parent, item.GetText())
    dlg.ShowModal()
    answer = dlg.GetAnswer()

    if answer == ID_PROMPT_YES:

        method(None, item, *args)  # passed OnDelete<item> method


# -------------------------------------------------------------------------------------------------------------------- #

def DeleteMultipleTreeItems(parent, items, method, *args):
    answer = None
    yestoall = False
    n = len(items)

    for item in items:

        if not yestoall:

            if n > 1:
                dlg = DeleteItemsDialog(parent, item.GetText())
            else:
                dlg = DeleteItemDialog(parent, item.GetText())

            dlg.ShowModal()
            answer = dlg.GetAnswer()

        if yestoall or (answer in (ID_PROMPT_YES, ID_PROMPT_YESTOALL)):

            method(None, item, *args)  # passed OnDelete<item> method

            if answer == ID_PROMPT_YESTOALL:
                yestoall = True

        elif answer == ID_PROMPT_NO:

            pass

        elif answer == ID_PROMPT_CANCEL:

            return

        else:

            pass

        n -= 1


# -------------------------------------------------------------------------------------------------------------------- #
def MoveFolderOntoFolder(parent, target, item):
    dlg = MoveFolderDialog(parent, target.GetText())
    dlg.ShowModal()
    answer = dlg.GetAnswer()

    if answer == ID_PROMPT_YES:
        index = target.GetChildrenCount() - 1
        drop_target = target
    else:
        index = RelativeDragIndex(target, item)
        drop_target = target.GetParent()

    return index, drop_target


# -------------------------------------------------------------------------------------------------------------------- #
def RelativeDragIndex(target, item):
    # used in case target is of similar type as dragged item and they have the same parent

    same_parent = target.GetParent() is item.GetParent()
    children = target.GetParent().GetChildren()
    index_t = children.index(target)

    if same_parent:
        index_i = children.index(item)

        # if items are moved up from below the target, then put them above, else below
        if index_t < index_i:
            return index_t - 1
        else:
            return index_t

    else:
        return index_t
