# /home/ghost/Desktop/projects/a2a-fraud-detection/main.py
from nicegui import ui, app
from datetime import datetime
import config
import fraud_engine
import database

# --- Helper Functions ---
def get_text(key):
    """Retrieves text based on selected language."""
    lang = app.storage.user.get('lang', 'EN')
    return config.TRANSLATIONS[lang].get(key, key)

async def reload_page():
    """Robust reload that works across NiceGUI versions."""
    await ui.run_javascript('window.location.reload()')

@ui.page('/')
def index():
    # --- State Management ---
    # Initialize storage defaults if not present
    if 'lang' not in app.storage.user:
        app.storage.user['lang'] = 'TR' # Default to TR as requested
    if 'segments' not in app.storage.user:
        app.storage.user['segments'] = database.get_all_segments() # Fetch from DB
    if 'maintenance' not in app.storage.user:
        app.storage.user['maintenance'] = False
    if 'global_cap' not in app.storage.user:
        app.storage.user['global_cap'] = database.get_global_cap()

    # --- Theme Settings ---
    ui.dark_mode().enable()

    # --- Header ---
    with ui.header().classes(replace='row items-center') as header:
        header.classes('bg-slate-900 text-white')
        ui.icon('shield', size='32px').classes('mr-2')
        ui.label(get_text('app_title')).classes('text-h6 font-bold')
        
        ui.space()
        
        # Language Switcher
        async def toggle_lang():
            new_lang = 'TR' if app.storage.user['lang'] == 'EN' else 'EN'
            app.storage.user['lang'] = new_lang
            await reload_page()
            
        ui.button(app.storage.user['lang'], on_click=toggle_lang).props('flat color=white')

    # --- Left Drawer (Sidebar) ---
    # value=True prevents client-side sync timeout on load
    with ui.left_drawer(value=True).classes('bg-grey-9') as drawer:
        ui.label(get_text('nav_title')).classes('text-grey-4 text-caption q-mb-sm q-ml-sm')
        
        # Simple Navigation using Tabs logic
        with ui.tabs().props('vertical').classes('w-full') as tabs:
            tab_dash = ui.tab(get_text('tab_dashboard'), icon='dashboard')
            tab_sim = ui.tab(get_text('tab_simulation'), icon='science')
            tab_hist = ui.tab(get_text('tab_history'), icon='history')
            tab_set = ui.tab(get_text('tab_settings'), icon='settings')

    # --- Action Dialog Logic (Shared) ---
    action_dialog = ui.dialog()
    # State to hold current transaction ID being acted upon
    current_action_ctx = {'id': None, 'type': None}
    comment_input = None # Will be initialized inside dialog

    with action_dialog, ui.card():
        ui.label(get_text('dlg_action_title')).classes('text-h6')
        comment_input = ui.input(get_text('lbl_reason')).classes('w-full')
        
        async def submit_action():
            if not comment_input.value.strip():
                ui.notify(get_text('err_comment_req'), type='negative')
                return
            
            new_status = 'APPROVED' if current_action_ctx['type'] == 'approve' else 'REJECT'
            risk = 0.0 if new_status == 'APPROVED' else 1.0
            # Append comment to reason
            full_reason = f"{comment_input.value} (Manual {new_status})"
            
            database.update_transaction_status(current_action_ctx['id'], risk, new_status, full_reason)
            msg_key = 'msg_trans_approved' if new_status == 'APPROVED' else 'msg_trans_rejected'
            ui.notify(get_text(msg_key), type='positive' if new_status == 'APPROVED' else 'warning')
            action_dialog.close()
            await reload_page()

        ui.button(get_text('btn_approve'), on_click=submit_action).bind_visibility_from(current_action_ctx, 'type', backward=lambda x: x == 'approve')
        ui.button(get_text('btn_reject'), on_click=submit_action).bind_visibility_from(current_action_ctx, 'type', backward=lambda x: x == 'reject').props('color=negative')

    def open_action_dialog(e):
        data = e.args
        current_action_ctx['id'] = data['row']['id']
        current_action_ctx['type'] = data['type']
        comment_input.value = "" # Reset comment
        action_dialog.open()

    # --- Main Content Area ---
    with ui.tab_panels(tabs, value=tab_dash).classes('w-full p-4'):
        
        # === TAB 1: DASHBOARD ===
        with ui.tab_panel(tab_dash):
            ui.label(get_text('tab_dashboard')).classes('text-h4 q-mb-md')
            
            # Refresh Button
            with ui.row().classes('w-full justify-end q-mb-sm'):
                ui.button(get_text('btn_refresh'), icon='refresh', on_click=reload_page).props('flat color=primary')

            # --- Statistics Section ---
            stats = database.get_dashboard_stats()
            with ui.grid(columns=4).classes('w-full gap-4 q-mb-md'):
                def stat_card(label, value, subtext, color='bg-blue-9'):
                    with ui.card().classes(f'w-full {color} p-2'):
                        ui.label(label).classes('text-caption font-bold text-white')
                        ui.label(value).classes('text-h6')
                        ui.label(subtext).classes('text-xs text-grey-3')

                stat_card(get_text('stat_daily'), 
                          f"${stats['day_total_amt']:,.0f}", 
                          f"{stats['day_total_cnt']} Adet")
                
                stat_card(get_text('stat_suspicious'), 
                          f"${stats['suspicious_amt']:,.0f}", 
                          f"{stats['suspicious_cnt']} Adet", color='bg-red-9')
                
                stat_card(get_text('stat_monitor'), 
                          f"${stats['monitor_amt']:,.0f}", 
                          f"{stats['monitor_cnt']} Adet", color='bg-orange-9')
                          
                stat_card(get_text('stat_queued'), 
                          f"{stats['queued_cnt']}", 
                          get_text('stat_queued_pending'), color='bg-grey-8')
            
            # --- Dashboard Panels (Suspicious & Monitor) ---
            with ui.grid(columns=2).classes('w-full gap-4'):
                # Panel 1: Suspicious
                with ui.card().classes('w-full'):
                    ui.label(get_text('stat_suspicious_recent')).classes('text-h6 text-negative')
                    susp_rows = database.get_recent_transactions_by_status('REJECT', 50)
                    # Pre-format rows to avoid lambda in columns (JSON serialization fix)
                    for r in susp_rows:
                        r['amount'] = f"${r['amount']:,.0f}"

                    ui.table(
                        columns=[
                            {'name': 'sender', 'label': get_text('lbl_sender'), 'field': 'sender', 'align': 'left'},
                            {'name': 'amount', 'label': get_text('lbl_amount'), 'field': 'amount', 'align': 'right'},
                            {'name': 'reason', 'label': get_text('lbl_reason'), 'field': 'reason', 'align': 'left'}
                        ],
                        rows=susp_rows,
                        row_key='id'
                    ).classes('w-full').props('dense flat')

                # Panel 2: Monitor
                with ui.card().classes('w-full'):
                    ui.label(get_text('stat_monitor_recent')).classes('text-h6 text-warning')
                    mon_rows = database.get_recent_transactions_by_status('MONITOR', 50)
                    # Pre-format rows to avoid lambda in columns (JSON serialization fix)
                    for r in mon_rows:
                        r['amount'] = f"${r['amount']:,.0f}"

                    mon_cols = [
                        {'name': 'sender', 'label': get_text('lbl_sender'), 'field': 'sender', 'align': 'left'},
                        {'name': 'amount', 'label': get_text('lbl_amount'), 'field': 'amount', 'align': 'right'},
                        {'name': 'reason', 'label': get_text('lbl_reason'), 'field': 'reason', 'align': 'left'},
                        {'name': 'actions', 'label': get_text('lbl_actions'), 'field': 'actions', 'align': 'center'}
                    ]

                    with ui.table(columns=mon_cols, rows=mon_rows, row_key='id').classes('w-full').props('dense flat') as mon_table:
                        mon_table.add_slot('body-cell-actions', '''
                            <q-td :props="props">
                                <q-btn icon="check" color="positive" flat dense size="sm"
                                    @click="$parent.$emit('open_action', {row: props.row, type: 'approve'})" />
                                <q-btn icon="block" color="negative" flat dense size="sm"
                                    @click="$parent.$emit('open_action', {row: props.row, type: 'reject'})" />
                            </q-td>
                        ''')
                        
                        mon_table.on('open_action', open_action_dialog)

        # === TAB 2: SIMULATION ===
        with ui.tab_panel(tab_sim):
            ui.label(get_text('tab_simulation')).classes('text-h4 q-mb-md')
            ui.label(get_text('lbl_manual_entry')).classes('text-subtitle1 text-grey-5 q-mb-md')

            
            # Maintenance Check
            if app.storage.user['maintenance']:
                with ui.row().classes('w-full bg-warning text-white p-2 rounded q-mb-md items-center'):
                    ui.icon('warning', size='sm').classes('mr-2')
                    ui.label(get_text('msg_maint'))

            with ui.card().classes('w-full max-w-3xl'):
                with ui.grid(columns=2).classes('w-full gap-4'):
                    # Inputs are always enabled now, but action changes based on maintenance
                    sender = ui.input(get_text('lbl_sender'), value='USR-1001').props('outlined').tooltip(get_text('tip_sender'))
                    receiver = ui.input(get_text('lbl_receiver'), value='USR-2055').props('outlined').tooltip(get_text('tip_sender'))
                    
                    amount = ui.number(get_text('lbl_amount'), value=5000.0, format='%.2f').props('outlined').tooltip(get_text('tip_amount'))
                    
                    # Free Text Time Input
                    time_input = ui.input(get_text('lbl_time'), value='14:30', placeholder='HH:MM').props('outlined').tooltip(get_text('tip_time'))
                    
                    segment = ui.select(app.storage.user['segments'], label=get_text('lbl_segment'), value='Individual').props('outlined')
                    is_intl = ui.checkbox(get_text('lbl_intl'))

                ui.separator().classes('q-my-md')

                def run_analysis():
                    # Parse Time
                    try:
                        h, m = map(int, time_input.value.split(':'))
                        # Construct timestamp for DB
                        now = datetime.now()
                        txn_ts = now.replace(hour=h, minute=m, second=0, microsecond=0)
                    except:
                        ui.notify(get_text('err_time_fmt'), type='negative')
                        return

                    # Maintenance Mode Logic
                    if app.storage.user['maintenance']:
                        db_record = {
                            'timestamp': txn_ts,
                            'sender': sender.value,
                            'receiver': receiver.value,
                            'amount': amount.value,
                            'segment': segment.value,
                            'risk_score': 0.0,
                            'status': 'QUEUED',
                            'reason': 'Maintenance Mode - Pending Analysis'
                        }
                        database.add_transaction(db_record)
                        ui.notify(get_text('msg_queued'), type='warning', icon='save')
                        return
                    
                    
                    # Call Engine
                    res = fraud_engine.analyze_transaction(
                        sender=sender.value,
                        receiver=receiver.value,
                        amount=amount.value,
                        hour=h,
                        minute=m,
                        segment=segment.value,
                        is_intl=is_intl.value
                    )
                    
                    # Determine UI Feedback
                    color_map = {"APPROVED": "positive", "MONITOR": "warning", "REJECT": "negative"}
                    
                    # Translation Logic for Reason
                    reason_key = res.get('reason_key')
                    translated_reason = get_text(reason_key) if reason_key else res['reason']
                    
                    # Show Notification
                    ui.notify(
                        f"{res['status']}: {translated_reason}", 
                        type=color_map.get(res['status'], 'info'),
                        position='top',
                        close_button=True,
                        timeout=5000
                    )
                    
                    # Show Dialog
                    with ui.dialog() as dialog, ui.card():
                        ui.label(get_text(f"res_{res['status'].lower()}")).classes(f'text-h5 text-{color_map[res["status"]]} font-bold')
                        ui.label(f"{get_text('lbl_reason')}: {translated_reason}")
                        ui.label(f"{get_text('hist_risk')}: {res['risk_score']:.4f}")
                        ui.button(get_text('btn_close'), on_click=dialog.close)
                    dialog.open()
                    
                    # Save to DB
                    db_record = {
                        'timestamp': txn_ts,
                        'sender': sender.value,
                        'receiver': receiver.value,
                        'amount': amount.value,
                        'segment': segment.value,
                        'risk_score': res['risk_score'],
                        'status': res['status'],
                        'reason': res['reason']
                    }
                    database.add_transaction(db_record)

                btn_text = get_text('btn_queue') if app.storage.user['maintenance'] else get_text('btn_analyze')
                btn_color = "warning" if app.storage.user['maintenance'] else "primary"
                ui.button(btn_text, on_click=run_analysis).props(f'color={btn_color} size=lg').classes('w-full')

        # === TAB 3: HISTORY ===
        with ui.tab_panel(tab_hist):
            ui.label(get_text('tab_history')).classes('text-h4 q-mb-md')
            
            # Filters
            with ui.row().classes('w-full gap-4 q-mb-md'):
                filter_status = ui.select(['ALL', 'APPROVED', 'MONITOR', 'REJECT', 'QUEUED'], value='ALL', label=get_text('filter_status')).classes('w-40')
                filter_sender = ui.input(get_text('lbl_sender')).classes('w-40')
                
                def apply_filters():
                    # Trigger table update
                    history_table.update()

            # Table Columns
            cols = [
                {'name': 'date', 'label': get_text('hist_date'), 'field': 'date', 'align': 'left'},
                {'name': 'sender', 'label': get_text('hist_sender'), 'field': 'sender', 'align': 'left'},
                {'name': 'amount', 'label': get_text('hist_amount'), 'field': 'amount', 'align': 'right'},
                {'name': 'risk', 'label': get_text('hist_risk'), 'field': 'risk', 'align': 'center'},
                {'name': 'status', 'label': get_text('hist_status'), 'field': 'status', 'align': 'center'},
                {'name': 'actions', 'label': get_text('lbl_actions'), 'field': 'actions', 'align': 'center'}
            ]
            
            # Fetch and Filter Logic
            db_rows = database.get_history(200) # Fetch more to allow filtering
            
            def get_filtered_rows():
                filtered = []
                for r in db_rows:
                    # Status Filter
                    if filter_status.value != 'ALL' and r['status'] != filter_status.value:
                        continue
                    # Sender Filter
                    if filter_sender.value and filter_sender.value not in r['sender']:
                        continue
                        
                    filtered.append({
                        'date': r['timestamp'],
                        'sender': r['sender'],
                        'amount': r['amount'],
                        'risk': f"{r['risk_score']:.2f}",
                        'status': r['status'],
                        'reason': r['reason'] if 'reason' in r.keys() else '',
                        'id': r['id'] # Needed for actions
                    })
                return filtered

            def update_history_table():
                history_table.rows = get_filtered_rows()
                history_table.update()

            history_table = ui.table(columns=cols, rows=get_filtered_rows(), row_key='id').classes('w-full')
            
            # Add Actions Slot
            history_table.add_slot('body-cell-actions', '''
                <q-td :props="props">
                    <div v-if="props.row.status === 'MONITOR'">
                        <q-btn icon="check" color="positive" flat dense size="sm" @click="$parent.$emit('open_action', {row: props.row, type: 'approve'})" />
                        <q-btn icon="block" color="negative" flat dense size="sm" @click="$parent.$emit('open_action', {row: props.row, type: 'reject'})" />
                    </div>
                    <div v-else>
                        -
                    </div>
                </q-td>
            ''')
            
            history_table.on('open_action', open_action_dialog)
            
            # Bind filters to update
            filter_status.on_value_change(update_history_table)
            filter_sender.on_value_change(update_history_table)
            
            ui.button(get_text('btn_refresh'), on_click=reload_page).props('flat color=primary')

        # === TAB 4: SETTINGS ===
        with ui.tab_panel(tab_set):
            ui.label(get_text('tab_settings')).classes('text-h4 q-mb-md')
            
            with ui.card().classes('w-full max-w-lg'):
                ui.label(get_text('hdr_global_config')).classes('text-h6')
                
                # Global Cap
                g_cap = ui.number(get_text('lbl_global_cap'), value=app.storage.user['global_cap'], format='%.0f').classes('w-full').tooltip(get_text('tip_global_cap'))
                
                def save_global_cap():
                    database.set_global_cap(g_cap.value)
                    app.storage.user['global_cap'] = g_cap.value
                    ui.notify("Global Cap Updated", type='positive')
                    
                ui.button(get_text('btn_update_cap'), on_click=save_global_cap).classes('w-full q-mt-sm')
                
                # Refresh Button for Settings
                ui.button(get_text('btn_refresh'), icon='refresh', on_click=reload_page).props('flat color=secondary').classes('w-full q-mt-sm')
                
                ui.separator().classes('q-my-md')
                
                # --- Advanced Rules Config ---
                ui.label(get_text('hdr_adv_rules')).classes('text-h6')
                with ui.grid(columns=2).classes('w-full gap-2'):
                    cfg_night_start = ui.number(get_text('cfg_night_start'), value=database.get_config('night_start', 0))
                    cfg_night_end = ui.number(get_text('cfg_night_end'), value=database.get_config('night_end', 6))
                    cfg_night_ratio = ui.number(get_text('cfg_night_ratio'), value=database.get_config('night_ratio', 0.8), format='%.2f')
                    cfg_hist_mult = ui.number(get_text('cfg_hist_mult'), value=database.get_config('hist_multiplier', 5.0))
                
                def save_adv_rules():
                    database.set_config('night_start', int(cfg_night_start.value))
                    database.set_config('night_end', int(cfg_night_end.value))
                    database.set_config('night_ratio', float(cfg_night_ratio.value))
                    database.set_config('hist_multiplier', float(cfg_hist_mult.value))
                    ui.notify("Advanced Rules Updated", type='positive')
                    
                ui.button(get_text('btn_save_adv'), on_click=save_adv_rules).classes('w-full q-mt-sm')
                
                ui.separator().classes('q-my-md')

                ui.label(get_text('hdr_segment_rules')).classes('text-h6')
                
                # Segment Selector
                # Use a key to force re-render when segments change
                seg_select = ui.select(app.storage.user['segments'], label=get_text('lbl_select_seg_edit')).classes('w-full')
                
                # Rule Inputs
                with ui.grid(columns=2).classes('w-full gap-2'):
                    min_amt = ui.number(get_text('lbl_min_amt'))
                    max_amt = ui.number(get_text('lbl_max_amt'))
                    daily_lim = ui.number(get_text('lbl_daily_lim'))
                    monthly_lim = ui.number(get_text('lbl_monthly_lim'))
                
                def load_rules(e):
                    rules = database.get_segment_rules(e.value)
                    if rules:
                        min_amt.value = rules['min_amount']
                        max_amt.value = rules['max_amount']
                        daily_lim.value = rules['daily_limit']
                        monthly_lim.value = rules['monthly_limit']
                
                seg_select.on_value_change(load_rules)
                
                def save_rules():
                    if seg_select.value:
                        database.update_segment_rules(
                            seg_select.value, 
                            min_amt.value, 
                            max_amt.value, 
                            int(daily_lim.value), 
                            int(monthly_lim.value)
                        )
                        ui.notify(f"Rules updated for {seg_select.value}", type='positive')
                
                ui.button(get_text('btn_save_rules'), on_click=save_rules).classes('w-full q-mt-md')
                
                ui.separator().classes('q-my-md')
                
                # Add/Delete Segment
                with ui.expansion(get_text('hdr_segment_rules'), value=False):
                    new_seg_name = ui.input(get_text('lbl_new_seg_name'))
                    async def add_new_segment():
                        if new_seg_name.value:
                            database.add_segment(new_seg_name.value)
                            app.storage.user['segments'] = database.get_all_segments()
                            ui.notify(f"Segment {new_seg_name.value} added", type='positive')
                            await reload_page()
                    ui.button(get_text('btn_add_seg'), on_click=add_new_segment).classes('w-full q-mb-sm')
                    
                    del_seg_select = ui.select(app.storage.user['segments'], label=get_text('lbl_select_seg_del'))
                    async def delete_selected_segment():
                        if del_seg_select.value:
                            database.delete_segment(del_seg_select.value)
                            app.storage.user['segments'] = database.get_all_segments()
                            ui.notify(f"Segment {del_seg_select.value} deleted", type='negative')
                            await reload_page()
                    ui.button(get_text('btn_del_seg'), on_click=delete_selected_segment).props('color=negative').classes('w-full')

                ui.separator().classes('q-my-md')
                
                # --- List Management (Blacklist / Watchlist) ---
                ui.label(get_text('hdr_restricted_lists')).classes('text-h6')
                
                list_type_tab = ui.tabs().classes('w-full')
                with list_type_tab:
                    ui.tab('BLACKLIST', label=get_text('tab_blacklist'))
                    ui.tab('WATCHLIST', label=get_text('tab_watchlist'))
                
                with ui.tab_panels(list_type_tab, value='BLACKLIST').classes('w-full'):
                    
                    # Helper to render list table
                    def render_list_panel(l_type):
                        with ui.tab_panel(l_type):
                            # Add Form
                            with ui.row().classes('w-full gap-2 items-end'):
                                l_id = ui.input(get_text('lbl_entity_id')).classes('flex-grow')
                                l_reason = ui.input(get_text('lbl_reason')).classes('flex-grow')
                                
                                async def add_to_list_cb():
                                    if l_id.value:
                                        database.manage_list("add", l_type, l_id.value, l_reason.value)
                                        ui.notify(f"{get_text('msg_added_to')} {l_type}", type='positive')
                                        await reload_page() # Refresh to show in table
                                
                                ui.button(get_text('btn_add_seg'), on_click=add_to_list_cb) # Reusing 'Add' button text
                            
                            ui.separator().classes('q-my-sm')
                            
                            # List Table
                            rows = database.get_list_details(l_type)
                            cols = [
                                {'name': 'entity_id', 'label': 'ID', 'field': 'entity_id', 'align': 'left'},
                                {'name': 'reason', 'label': get_text('lbl_reason'), 'field': 'reason', 'align': 'left'},
                                {'name': 'added_on', 'label': get_text('lbl_added_on'), 'field': 'added_on', 'align': 'left'},
                                {'name': 'actions', 'label': get_text('lbl_actions'), 'field': 'actions'}
                            ]
                            
                            # Custom table with delete button
                            with ui.table(columns=cols, rows=rows, row_key='entity_id').classes('w-full') as table:
                                table.add_slot('body-cell-actions', '''
                                    <q-td :props="props">
                                        <q-btn icon="delete" color="negative" flat dense 
                                            @click="$parent.$emit('delete', props.row)" />
                                    </q-td>
                                ''')
                                
                                async def delete_entry(e):
                                    row = e.args
                                    database.manage_list("remove", l_type, row['entity_id'])
                                    ui.notify(f"{get_text('msg_removed')} {row['entity_id']}", type='info')
                                    await reload_page()
                                    
                                table.on('delete', delete_entry)

                    render_list_panel('BLACKLIST')
                    render_list_panel('WATCHLIST')
                
                ui.separator().classes('q-my-md')
                
                ui.label(get_text('hdr_system_controls')).classes('text-h6')
                
                # Maintenance Switch
                async def toggle_maint(e):
                    app.storage.user['maintenance'] = e.value
                    await reload_page() # Reload to update UI state
                    
                ui.switch(get_text('lbl_maint'), value=app.storage.user['maintenance'], on_change=toggle_maint).classes('q-mb-md')
                
                # Process Queue Button
                async def process_queue():
                    queued = database.get_queued_transactions()
                    if not queued:
                        ui.notify(get_text('msg_no_queue'), type='info')
                        return
                    
                    count = 0
                    for txn in queued:
                        # Parse timestamp from DB string
                        ts_str = txn['timestamp']
                        # Simple parsing assuming standard SQLite format, or just use 00:00 if complex
                        # For engine features, we need hour/minute
                        try:
                            dt = datetime.fromisoformat(ts_str)
                            h, m = dt.hour, dt.minute
                        except:
                            h, m = 0, 0
                            
                        res = fraud_engine.analyze_transaction(txn['sender'], txn['receiver'], txn['amount'], h, m, txn['segment'], False)
                        database.update_transaction_status(txn['id'], res['risk_score'], res['status'], res['reason'])
                        count += 1
                    
                    ui.notify(get_text('msg_processed_queue').format(count=count), type='positive')
                    await reload_page() # Refresh stats
                
                ui.button(get_text('btn_process_queue'), on_click=process_queue).props('color=secondary').classes('w-full')

# Run the app with a storage secret for persistence
database.init_db()
app.on_startup(fraud_engine.train_models)
ui.run(title="Shield AML", storage_secret='super_secret_aml_key_123')
