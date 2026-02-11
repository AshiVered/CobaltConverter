import wx

from cobalt_converter.utils import get_ffmpeg_version


class UIBuilderMixin:
    def _build_ui(self) -> None:
        self.main_panel = wx.Panel(self)
        panel = self.main_panel
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        panel.SetSizer(main_sizer)
        main_sizer.SetMinSize((600, 400))

        top_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.select_btn = wx.Button(panel)
        self.select_btn.Bind(wx.EVT_BUTTON, lambda e: self.select_files())
        top_sizer.Add(self.select_btn, 0, wx.RIGHT, 6)

        self.clear_btn = wx.Button(panel)
        self.clear_btn.Bind(wx.EVT_BUTTON, lambda e: self.clear_files())
        top_sizer.Add(self.clear_btn, 0, wx.RIGHT, 6)

        top_sizer.AddStretchSpacer(1)

        self.language_label = wx.StaticText(panel)
        top_sizer.Add(self.language_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.language_choice = wx.ComboBox(panel, choices=["English", "עברית"], style=wx.CB_READONLY)
        self.language_choice.Bind(wx.EVT_COMBOBOX, lambda e: self.change_language(self.language_choice.GetValue()))
        top_sizer.Add(self.language_choice, 0)

        main_sizer.Add(top_sizer, 0, wx.EXPAND | wx.ALL, 8)

        self.scroll = wx.ScrolledWindow(panel, style=wx.VSCROLL)
        self.scroll.SetScrollRate(5, 5)
        self.list_sizer = wx.BoxSizer(wx.VERTICAL)
        self.scroll.SetSizer(self.list_sizer)
        self.list_sizer.AddStretchSpacer(1)
        main_sizer.Add(self.scroll, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        self.drag_hint = wx.StaticText(panel)
        self.drag_hint.Wrap(600)
        self.drag_hint.SetForegroundColour(wx.Colour(128, 128, 128))
        main_sizer.Add(self.drag_hint, 0, wx.EXPAND | wx.ALL, 6)

        out_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.use_custom_output = wx.CheckBox(panel)
        self.use_custom_output.Bind(wx.EVT_CHECKBOX, self._toggle_output_folder)
        out_sizer.Add(self.use_custom_output, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 6)

        self.output_folder_edit = wx.TextCtrl(panel)
        self.output_folder_edit.Enable(False)
        out_sizer.Add(self.output_folder_edit, 1, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)

        self.browse_output_btn = wx.Button(panel)
        self.browse_output_btn.Bind(wx.EVT_BUTTON, lambda e: self._select_output_folder())
        self.browse_output_btn.Enable(False)
        out_sizer.Add(self.browse_output_btn, 0)

        main_sizer.Add(out_sizer, 0, wx.EXPAND | wx.ALL, 8)

        format_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.format_label = wx.StaticText(panel)
        format_sizer.Add(self.format_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.format_combo = wx.ComboBox(panel, choices=[], style=wx.CB_READONLY)
        self.format_combo.SetMinSize((150, -1))
        self.format_combo.Bind(wx.EVT_COMBOBOX, lambda e: self._on_format_changed())
        format_sizer.Add(self.format_combo, 0, wx.RIGHT, 12)

        self.quality_label = wx.StaticText(panel)
        format_sizer.Add(self.quality_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.quality_combo = wx.ComboBox(panel, style=wx.CB_READONLY)
        self.quality_combo.SetMinSize((150, -1))
        self.quality_combo.Bind(wx.EVT_COMBOBOX, lambda e: self._on_quality_changed())
        format_sizer.Add(self.quality_combo, 0, wx.RIGHT, 6)

        format_sizer.AddStretchSpacer(1)
        main_sizer.Add(format_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)

        self.custom_panel = wx.Panel(panel)
        self.custom_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.custom_panel.SetSizer(self.custom_sizer)
        self.custom_panel.Hide()
        main_sizer.Add(self.custom_panel, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        self.custom_controls: dict[str, wx.Window] = {}
        self.custom_value_labels: dict[str, wx.StaticText] = {}

        self.progress_bar = wx.Gauge(panel, range=100)
        main_sizer.Add(self.progress_bar, 0, wx.EXPAND | wx.ALL, 8)
        self.status_label = wx.StaticText(panel, label="")
        main_sizer.Add(self.status_label, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.convert_btn = wx.Button(panel)
        self.convert_btn.Bind(wx.EVT_BUTTON, lambda e: self.start_conversion())
        self.convert_btn.SetMinSize((-1, 35))
        btn_sizer.Add(self.convert_btn, 0, wx.RIGHT, 6)

        self.stop_btn = wx.Button(panel)
        self.stop_btn.Bind(wx.EVT_BUTTON, lambda e: self._stop_conversion())
        self.stop_btn.Enable(False)
        self.stop_btn.SetMinSize((-1, 35))
        btn_sizer.Add(self.stop_btn, 0)

        main_sizer.Add(btn_sizer, 0, wx.ALIGN_LEFT | wx.ALL, 8)

        footer_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.footer_label = wx.StaticText(panel)
        self.footer_label.SetForegroundColour(wx.Colour(128, 128, 128))
        footer_sizer.AddStretchSpacer(1)
        footer_sizer.Add(self.footer_label, 0, wx.ALIGN_CENTER_VERTICAL)
        footer_sizer.AddStretchSpacer(1)
        main_sizer.Add(footer_sizer, 0, wx.EXPAND | wx.ALL, 4)

        self._retranslate_ui()

    def _on_format_changed(self) -> None:
        self._update_quality_options()

    def _on_quality_changed(self) -> None:
        selected = self.quality_combo.GetValue()
        is_custom = selected == self.translator.get("quality_custom")
        if is_custom:
            self._build_custom_controls()
            self.custom_panel.Show()
        else:
            self.custom_panel.Hide()
        self.main_panel.Layout()
        self.Layout()

    def _update_quality_options(self) -> None:
        output_format = self.format_combo.GetValue()
        t = self.translator

        self.quality_combo.Clear()
        self.custom_panel.Hide()

        if not output_format or self.quality_manager.is_lossless(output_format):
            self.quality_combo.Enable(False)
            self.quality_combo.Append(t.get("quality_default"))
            self.quality_combo.SetSelection(0)
            return

        self.quality_combo.Enable(True)
        choices = [
            t.get("quality_default"),
            t.get("quality_low"),
            t.get("quality_medium"),
            t.get("quality_high"),
            t.get("quality_maximum"),
            t.get("quality_custom"),
        ]
        for choice in choices:
            self.quality_combo.Append(choice)
        self.quality_combo.SetSelection(0)
        self.Layout()

    def _build_custom_controls(self) -> None:
        self.custom_sizer.Clear(delete_windows=True)
        self.custom_controls.clear()
        self.custom_value_labels.clear()

        output_format = self.format_combo.GetValue()
        if not output_format:
            return

        params = self.quality_manager.get_custom_params(output_format)
        for param in params:
            name = param["name"]
            label = wx.StaticText(self.custom_panel, label=f"{name}:")
            self.custom_sizer.Add(label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4)

            if param["type"] == "slider":
                slider = wx.Slider(
                    self.custom_panel,
                    value=param["default"],
                    minValue=param["min"],
                    maxValue=param["max"],
                    style=wx.SL_HORIZONTAL,
                )
                slider.SetMinSize((150, -1))
                self.custom_sizer.Add(slider, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4)
                self.custom_controls[name] = slider

                suffix = param.get("suffix", "")
                value_label = wx.StaticText(self.custom_panel, label=f"{param['default']}{suffix}")
                self.custom_sizer.Add(value_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 12)
                self.custom_value_labels[name] = value_label

                slider.Bind(wx.EVT_SLIDER, lambda e, n=name, s=suffix: self._on_custom_slider_changed(n, s))

            elif param["type"] == "choice":
                combo = wx.ComboBox(
                    self.custom_panel,
                    choices=param["options"],
                    style=wx.CB_READONLY,
                )
                combo.SetValue(param["default"])
                self.custom_sizer.Add(combo, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 12)
                self.custom_controls[name] = combo

        self.custom_panel.Layout()
        self.Layout()

    def _on_custom_slider_changed(self, param_name: str, suffix: str) -> None:
        slider = self.custom_controls[param_name]
        value = slider.GetValue()
        if param_name in self.custom_value_labels:
            self.custom_value_labels[param_name].SetLabel(f"{value}{suffix}")

    def change_language(self, lang_name: str) -> None:
        lang_code = "he" if lang_name == "עברית" else "en"
        self.translator.set_language(lang_code)
        try:
            if lang_code == "he":
                self.SetLayoutDirection(wx.Layout_RightToLeft)
            else:
                self.SetLayoutDirection(wx.Layout_LeftToRight)
        except AttributeError:
            pass
        self._retranslate_ui()
        self.Layout()

    def _retranslate_ui(self) -> None:
        t = self.translator
        self.SetTitle(t.get("window_title"))
        self.select_btn.SetLabel(t.get("select_files_btn"))
        self.clear_btn.SetLabel(t.get("clear_btn"))
        self.drag_hint.SetLabel(t.get("drag_drop_hint"))
        self.use_custom_output.SetLabel(t.get("custom_output_checkbox"))
        self.output_folder_edit.SetHint(t.get("output_folder_placeholder"))
        self.browse_output_btn.SetLabel(t.get("browse_btn"))
        self.format_label.SetLabel(t.get("convert_to_label"))
        self.quality_label.SetLabel(t.get("quality_label"))
        self.convert_btn.SetLabel(t.get("convert_now_btn"))
        self.stop_btn.SetLabel(t.get("stop_btn"))
        self.language_label.SetLabel(t.get("language_label"))

        ffmpeg_path = self.engine.get_ffmpeg_path()
        ffmpeg_version = get_ffmpeg_version(ffmpeg_path)
        footer_text = t.get("footer")
        if ffmpeg_version:
            footer_text += f"  |  FFmpeg {ffmpeg_version}"
        else:
            footer_text += f"  |  FFmpeg: {t.get('ffmpeg_not_installed')}"
        self.footer_label.SetLabel(footer_text)

        if not self.is_converting:
            current_status = self.status_label.GetLabel()
            if current_status in ["", t.get("status_ready")]:
                self.status_label.SetLabel(t.get("status_ready"))

        self._update_quality_options()
