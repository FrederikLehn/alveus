import wx
from pubsub import pub

from frames.frame_design import ObjectFrame, SectionSeparator, SMALL_GAP
from frames.property_panels import PropertiesAUIPanel, SelectionTree, NormalSizeOptionsPanel, PresentSizeOptionsPanel,\
                                        UnitSystemPanel, EnsembleCasePanel, EnsembleShadingPanel

import _icons as ico


class SettingsFrame(ObjectFrame):
    def __init__(self, parent, settings, variable_page):
        super().__init__(parent=parent, title='Settings')

        self._settings = settings
        self._variable_page = variable_page

        # aui ----------------------------------------------------------------------------------------------------------
        self.aui_panel = PropertiesAUIPanel(self.custom, min_size=(245, 320))

        # general tab --------------------------------------------------------------------------------------------------
        general_panel = wx.Panel(self.custom)
        self.unit_system = UnitSystemPanel(general_panel)
        #
        self.aui_panel.AddPage(general_panel, self.unit_system,
                               title='General', bitmap=ico.producer_oil_gas_16x16.GetBitmap())

        # windows tab --------------------------------------------------------------------------------------------------
        window_panel = wx.Panel(self.custom)
        self.normal_options = NormalSizeOptionsPanel(window_panel)
        self.present_options = PresentSizeOptionsPanel(window_panel)

        self.aui_panel.AddPage(window_panel, self.normal_options, self.present_options,
                               title='Windows', bitmap=ico.windows_16x16.GetBitmap())

        # ensemble tab -------------------------------------------------------------------------------------------------
        ensemble_panel = wx.Panel(self.custom)
        self.cases = EnsembleCasePanel(ensemble_panel)
        self.shading = EnsembleShadingPanel(ensemble_panel)
        separator = SectionSeparator(ensemble_panel, label='Extraction objectives', bitmap=ico.summary_16x16.GetBitmap())
        self.extraction = SelectionTree(ensemble_panel, variable_page)

        self.aui_panel.AddPage(ensemble_panel, self.cases, self.shading, separator, self.extraction,
                               proportions=(0, 0, 0, 1), title='Ensemble', bitmap=ico.profiles_chart_16x16.GetBitmap())

        self.custom_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.InitUI()
        self.Load()

        self.SetSize(wx.Size(350, 600))
        self.SetMinSize(self.GetSize())
        self.Center()

        # events -------------------------------------------------------------------------------------------------------
        self.Bind(wx.EVT_BUTTON, self.OnApplyButton, self.apply_button)
        self.Bind(wx.EVT_BUTTON, self.OnOKButton, self.ok_button)

    def InitUI(self):
        self.SetIcon(ico.settings_16x16.GetIcon())

        # trees --------------------------------------------------------------------------------------------------------
        items = (self._variable_page.summaries,)
        self.extraction.Populate(items, ('summaries',), ct_type=1)

        # sizing input -------------------------------------------------------------------------------------------------
        self.aui_panel.Realize()
        self.custom_sizer.Add(self.aui_panel, 1, (wx.ALL & ~wx.TOP) | wx.EXPAND, SMALL_GAP)
        self.custom.SetSizer(self.custom_sizer)

        self.Realize()

    # events -----------------------------------------------------------------------------------------------------------
    def OnApplyButton(self, event):
        saved = self.Save()

        if saved:
            pub.sendMessage('settings_updated')

        return saved

    def OnOKButton(self, event):
        saved = self.OnApplyButton(None)

        if saved:
            self.Close(True)

    def Load(self):

        self.unit_system.Set(self._settings.GetUnitSystem())

        self.normal_options.Set(*self._settings.GetNormalSizeOptions().Get())
        self.present_options.Set(*self._settings.GetPresentSizeOptions().Get())

        self.cases.Set(*self._settings.GetCases())
        self.shading.Set(*self._settings.GetShading())

        self.extraction.CheckItemsById(self._settings.GetExtraction())

    def Save(self):

        self._settings.SetNormalSizeOptions(*self.normal_options.Get())
        self._settings.SetPresentSizeOptions(*self.present_options.Get())

        self._settings.SetCases(*self.cases.Get())
        self._settings.SetShading(*self.shading.Get())

        items = self.extraction.GetCheckedItems()
        self._settings.SetExtraction([i.GetData().GetId() for i in items])

        return True
