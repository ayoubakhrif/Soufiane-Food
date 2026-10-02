import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../services/storage_service.dart';
import 'main_navigation_screen.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final _loginController = TextEditingController();
  final _passwordController = TextEditingController();
  final _serverUrlController = TextEditingController();

  bool _isLoading = false;
  bool _obscurePassword = true;
  bool _showServerConfig = false;

  @override
  void initState() {
    super.initState();
    _loadSavedServerUrl();
  }

  Future<void> _loadSavedServerUrl() async {
    final url = await StorageService.getServerUrl();
    _serverUrlController.text = url;
  }

  @override
  void dispose() {
    _loginController.dispose();
    _passwordController.dispose();
    _serverUrlController.dispose();
    super.dispose();
  }

  Future<void> _handleLogin() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() => _isLoading = true);

    try {
      // Sauvegarder le serveur si modifié
      if (_serverUrlController.text.trim().isNotEmpty) {
        await StorageService.saveServerUrl(_serverUrlController.text.trim());
      }

      final session = await ApiService.login(
        _loginController.text.trim(),
        _passwordController.text.trim(),
      );

      if (!mounted) return;

      Navigator.pushReplacement(
        context,
        MaterialPageRoute(
          builder: (_) => MainNavigationScreen(session: session),
        ),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(e.toString().replaceAll('Exception: ', '')),
          backgroundColor: Colors.red.shade700,
          behavior: SnackBarBehavior.floating,
        ),
      );
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFC),
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 32),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 440),
              child: Form(
                key: _formKey,
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    // Logo / En-tête
                    Center(
                      child: Container(
                        padding: const EdgeInsets.all(22),
                        decoration: BoxDecoration(
                          color: const Color(0xFF0284C7).withOpacity(0.1),
                          shape: BoxShape.circle,
                        ),
                        child: const Icon(
                          Icons.account_balance_wallet_rounded,
                          size: 60,
                          color: Color(0xFF0284C7),
                        ),
                      ),
                    ),
                    const SizedBox(height: 24),

                    const Text(
                      'Suivi Budget',
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        fontSize: 28,
                        fontWeight: FontWeight.w800,
                        color: Color(0xFF0F172A),
                        letterSpacing: -0.5,
                      ),
                    ),
                    const SizedBox(height: 8),
                    const Text(
                      'Connectez-vous avec vos accès Odoo',
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        fontSize: 14,
                        color: Color(0xFF64748B),
                      ),
                    ),
                    const SizedBox(height: 36),

                    // Champ Identifiant
                    TextFormField(
                      controller: _loginController,
                      decoration: InputDecoration(
                        labelText: 'Identifiant / Nom d\'utilisateur',
                        prefixIcon: const Icon(Icons.person_outline_rounded),
                        filled: true,
                        fillColor: Colors.white,
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(14),
                          borderSide: BorderSide(color: Colors.grey.shade300),
                        ),
                        enabledBorder: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(14),
                          borderSide: BorderSide(color: Colors.grey.shade200),
                        ),
                      ),
                      validator: (v) =>
                          (v == null || v.trim().isEmpty) ? 'Veuillez saisir votre identifiant' : null,
                    ),
                    const SizedBox(height: 16),

                    // Champ Mot de passe
                    TextFormField(
                      controller: _passwordController,
                      obscureText: _obscurePassword,
                      decoration: InputDecoration(
                        labelText: 'Mot de passe',
                        prefixIcon: const Icon(Icons.lock_outline_rounded),
                        suffixIcon: IconButton(
                          icon: Icon(
                            _obscurePassword ? Icons.visibility_off_rounded : Icons.visibility_rounded,
                          ),
                          onPressed: () => setState(() => _obscurePassword = !_obscurePassword),
                        ),
                        filled: true,
                        fillColor: Colors.white,
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(14),
                          borderSide: BorderSide(color: Colors.grey.shade300),
                        ),
                        enabledBorder: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(14),
                          borderSide: BorderSide(color: Colors.grey.shade200),
                        ),
                      ),
                      validator: (v) =>
                          (v == null || v.trim().isEmpty) ? 'Veuillez saisir votre mot de passe' : null,
                    ),

                    const SizedBox(height: 12),

                    // Toggle pour URL serveur
                    Align(
                      alignment: Alignment.centerRight,
                      child: TextButton.icon(
                        onPressed: () => setState(() => _showServerConfig = !_showServerConfig),
                        icon: Icon(
                          _showServerConfig ? Icons.keyboard_arrow_up : Icons.settings_rounded,
                          size: 16,
                          color: const Color(0xFF64748B),
                        ),
                        label: Text(
                          _showServerConfig ? 'Masquer serveur' : 'Configurer serveur',
                          style: const TextStyle(fontSize: 12, color: Color(0xFF64748B)),
                        ),
                      ),
                    ),

                    if (_showServerConfig) ...[
                      const SizedBox(height: 4),
                      TextFormField(
                        controller: _serverUrlController,
                        decoration: InputDecoration(
                          labelText: 'URL Serveur Odoo',
                          prefixIcon: const Icon(Icons.dns_rounded),
                          filled: true,
                          fillColor: Colors.white,
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(14),
                          ),
                        ),
                      ),
                      const SizedBox(height: 12),
                    ],

                    const SizedBox(height: 18),

                    // Bouton de connexion
                    SizedBox(
                      height: 52,
                      child: ElevatedButton(
                        onPressed: _isLoading ? null : _handleLogin,
                        style: ElevatedButton.styleFrom(
                          backgroundColor: const Color(0xFF0284C7),
                          foregroundColor: Colors.white,
                          elevation: 0,
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(14),
                          ),
                        ),
                        child: _isLoading
                            ? const SizedBox(
                                width: 22,
                                height: 22,
                                child: CircularProgressIndicator(
                                  color: Colors.white,
                                  strokeWidth: 2.5,
                                ),
                              )
                            : const Text(
                                'Se connecter',
                                style: TextStyle(
                                  fontSize: 16,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                      ),
                    ),
                    const SizedBox(height: 18),

                    const Text(
                      'Vos identifiants seront mémorisés pour vos prochaines ouvertures.',
                      textAlign: TextAlign.center,
                      style: TextStyle(fontSize: 12, color: Color(0xFF94A3B8)),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
