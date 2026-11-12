//! The app is a thin shell: the bundled connect screen finds the hub on the UNO Q and then loads the
//! dashboard the hub serves, so the phone always shows the same controls as the web dashboard.

/// Starts the Tauri runtime. Called from `main` on desktop and from the Android activity on mobile.
#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .run(tauri::generate_context!())
        .expect("failed to start the Tauri runtime");
}
