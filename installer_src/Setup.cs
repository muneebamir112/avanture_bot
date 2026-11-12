using System;
using System.IO;
using System.Reflection;
using System.Diagnostics;
using System.Threading;
using System.Drawing;
using System.Windows.Forms;
using System.IO.Compression;

namespace AvantureInstaller
{
    static class Program
    {
        [STAThread]
        static void Main()
        {
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            Application.Run(new InstallerForm());
        }
    }

    public class InstallerForm : Form
    {
        private ProgressBar progressBar;
        private Label lblStatus;
        private Label lblTitle;
        private Label lblSub;
        private Label lblPercent;

        public InstallerForm()
        {
            this.Text = "Avanture Automation — Setup";
            this.Size = new Size(500, 250);
            this.StartPosition = FormStartPosition.CenterScreen;
            this.FormBorderStyle = FormBorderStyle.FixedDialog;
            this.MaximizeBox = false;
            this.MinimizeBox = false;
            this.BackColor = Color.FromArgb(15, 23, 42); // #0f172a Deep Dark Slate

            lblTitle = new Label();
            lblTitle.Text = "⚡ AVANTURE AUTOMATION";
            lblTitle.Font = new Font("Segoe UI", 14, FontStyle.Bold);
            lblTitle.ForeColor = Color.FromArgb(129, 140, 248); // #818cf8 Accent
            lblTitle.Location = new Point(24, 20);
            lblTitle.AutoSize = true;
            this.Controls.Add(lblTitle);

            lblSub = new Label();
            lblSub.Text = "Installing standalone engine & configuring Desktop shortcut...";
            lblSub.Font = new Font("Segoe UI", 9, FontStyle.Regular);
            lblSub.ForeColor = Color.FromArgb(148, 163, 184); // #94a3b8
            lblSub.Location = new Point(24, 52);
            lblSub.AutoSize = true;
            this.Controls.Add(lblSub);

            progressBar = new ProgressBar();
            progressBar.Location = new Point(24, 95);
            progressBar.Size = new Size(436, 26);
            progressBar.Style = ProgressBarStyle.Continuous;
            progressBar.Minimum = 0;
            progressBar.Maximum = 100;
            progressBar.Value = 0;
            this.Controls.Add(progressBar);

            lblPercent = new Label();
            lblPercent.Text = "0%";
            lblPercent.Font = new Font("Segoe UI", 9, FontStyle.Bold);
            lblPercent.ForeColor = Color.FromArgb(56, 189, 248); // #38bdf8
            lblPercent.Location = new Point(410, 130);
            lblPercent.Size = new Size(50, 20);
            lblPercent.TextAlign = ContentAlignment.MiddleRight;
            this.Controls.Add(lblPercent);

            lblStatus = new Label();
            lblStatus.Text = "Initializing setup...";
            lblStatus.Font = new Font("Segoe UI", 9, FontStyle.Regular);
            lblStatus.ForeColor = Color.FromArgb(203, 213, 225); // #cbd5e1
            lblStatus.Location = new Point(24, 130);
            lblStatus.Size = new Size(380, 20);
            this.Controls.Add(lblStatus);

            this.Shown += (s, e) => {
                ThreadPool.QueueUserWorkItem(DoInstallation);
            };
        }

        private void UpdateProgress(int percent, string message)
        {
            if (this.InvokeRequired)
            {
                this.BeginInvoke(new Action<int, string>(UpdateProgress), percent, message);
                return;
            }
            if (percent >= 0 && percent <= 100)
            {
                progressBar.Value = percent;
                lblPercent.Text = percent + "%";
            }
            if (!string.IsNullOrEmpty(message))
            {
                lblStatus.Text = message;
            }
        }

        private void DoInstallation(object state)
        {
            try
            {
                Thread.Sleep(300);
                UpdateProgress(5, "Preparing target directory...");

                string installDir = Path.Combine(
                    Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                    "AvantureAutomation"
                );

                if (!Directory.Exists(installDir))
                {
                    Directory.CreateDirectory(installDir);
                }

                UpdateProgress(10, "Extracting installation payload...");
                Assembly assembly = Assembly.GetExecutingAssembly();
                string tempZipPath = Path.Combine(Path.GetTempPath(), "avanture_setup_payload.zip");

                using (Stream stream = assembly.GetManifestResourceStream("payload.zip"))
                {
                    if (stream == null)
                    {
                        throw new Exception("Embedded installation payload not found.");
                    }
                    using (FileStream fileStream = new FileStream(tempZipPath, FileMode.Create, FileAccess.Write))
                    {
                        stream.CopyTo(fileStream);
                    }
                }

                UpdateProgress(20, "Unpacking runtime modules...");

                using (ZipArchive archive = ZipFile.OpenRead(tempZipPath))
                {
                    int total = archive.Entries.Count;
                    int processed = 0;

                    foreach (ZipArchiveEntry entry in archive.Entries)
                    {
                        processed++;
                        int currentPct = 20 + (int)((double)processed / total * 65.0);

                        string destinationPath = Path.GetFullPath(Path.Combine(installDir, entry.FullName));
                        if (entry.FullName.EndsWith("/") || entry.FullName.EndsWith("\\"))
                        {
                            Directory.CreateDirectory(destinationPath);
                            continue;
                        }

                        string parent = Path.GetDirectoryName(destinationPath);
                        if (!Directory.Exists(parent))
                        {
                            Directory.CreateDirectory(parent);
                        }

                        bool isUserDb = destinationPath.EndsWith("auth_system.db", StringComparison.OrdinalIgnoreCase);
                        bool isUserCreds = destinationPath.EndsWith(".avanture_creds.json", StringComparison.OrdinalIgnoreCase);

                        if ((isUserDb || isUserCreds) && File.Exists(destinationPath))
                        {
                            continue; // Preserve existing user database and credentials
                        }

                        try
                        {
                            entry.ExtractToFile(destinationPath, true);
                        }
                        catch
                        {
                            // Skip locked non-essential files if already present
                        }

                        if (processed % 40 == 0 || processed == total)
                        {
                            UpdateProgress(currentPct, "Installing: " + entry.Name);
                        }
                    }
                }

                try { File.Delete(tempZipPath); } catch { }

                UpdateProgress(90, "Creating Desktop and Start Menu shortcuts...");

                string exePath = Path.Combine(installDir, "AvantureAutomation.exe");

                // 1. Desktop Shortcut
                string desktopFolder = Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory);
                string desktopShortcut = Path.Combine(desktopFolder, "Avanture Automation.lnk");
                CreateShortcut(desktopShortcut, exePath, installDir, "Avanture Classifieds Automation");

                // 2. Start Menu Shortcut
                string startMenuFolder = Environment.GetFolderPath(Environment.SpecialFolder.Programs);
                string startMenuShortcut = Path.Combine(startMenuFolder, "Avanture Automation.lnk");
                CreateShortcut(startMenuShortcut, exePath, installDir, "Avanture Classifieds Automation");

                UpdateProgress(100, "Setup complete! Starting application...");
                Thread.Sleep(800);

                if (File.Exists(exePath))
                {
                    ProcessStartInfo psi = new ProcessStartInfo();
                    psi.FileName = exePath;
                    psi.WorkingDirectory = installDir;
                    Process.Start(psi);
                }

                this.Invoke(new Action(() => {
                    this.Close();
                }));
            }
            catch (Exception ex)
            {
                this.Invoke(new Action(() => {
                    MessageBox.Show(
                        "Installation Error: " + ex.Message,
                        "Avanture Setup Error",
                        MessageBoxButtons.OK,
                        MessageBoxIcon.Error
                    );
                    this.Close();
                }));
            }
        }

        private void CreateShortcut(string shortcutPath, string targetPath, string workingDir, string description)
        {
            try
            {
                Type shellType = Type.GetTypeFromProgID("WScript.Shell");
                if (shellType == null) return;
                dynamic shell = Activator.CreateInstance(shellType);
                dynamic shortcut = shell.CreateShortcut(shortcutPath);
                shortcut.TargetPath = targetPath;
                shortcut.WorkingDirectory = workingDir;
                shortcut.Description = description;
                shortcut.IconLocation = targetPath + ",0";
                shortcut.Save();
            }
            catch
            {
                // Fallback: ignore shortcut failure
            }
        }
    }
}
