//! Tauri shell for the offline try-out app (v6 AP-1).
//!
//! Deliberately thin: the exam engine, the question bank, and both update flows
//! live in the SPA. Rust only registers the plugins the frontend calls into,
//! plus the one thing a webview cannot do for itself (`print_page`).

/// FE-20 "Unduh PDF": `window.print()` is a no-op in the macOS WKWebView, so
/// the button did nothing in the app. Tauri drives the platform print dialog
/// natively instead — `NSPrintOperation` on macOS, the GTK print dialog on
/// Linux, `window.print()` on Windows, where it does work.
///
/// Android has no implementation behind it, and `WebviewWindow::print` is
/// desktop-only, so there the command reports failure rather than opening
/// nothing: the frontend hides the button instead of lying about it.
#[tauri::command]
fn print_page(window: tauri::WebviewWindow) -> Result<bool, String> {
    #[cfg(desktop)]
    {
        window.print().map_err(|err| err.to_string())?;
        Ok(true)
    }
    #[cfg(not(desktop))]
    {
        let _ = window;
        Ok(false)
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let builder = tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_process::init());

    // AP-6: desktop installs update in place through the signed `latest.json`.
    // Android has no updater implementation; AP-7 handles it in the frontend.
    #[cfg(desktop)]
    let builder = builder.plugin(tauri_plugin_updater::Builder::new().build());

    builder
        .invoke_handler(tauri::generate_handler![print_page])
        .setup(|app| {
            if cfg!(debug_assertions) {
                app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Info)
                        .build(),
                )?;
            }
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
