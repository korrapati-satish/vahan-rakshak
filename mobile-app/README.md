# Vahan Rakshak Mobile App

A Flutter-based mobile application for vehicle security and management.

## Overview

Vahan Rakshak is a comprehensive mobile application designed to enhance vehicle security and management. The app provides features like QR code scanning for vehicle verification, cargo form management, and secure authentication.

## Features

- **QR Code Scanning**: Easily scan and verify vehicle information
- **Cargo Form Management**: Digital cargo documentation and tracking
- **Secure Authentication**: Protected access through login system
- **Cross-Platform Support**: Works on Android, iOS, Web, and Desktop platforms

## Project Structure

```
lib/
├── main.dart              # Application entry point
├── login_page.dart        # User authentication interface
├── qr_scan_page.dart     # QR code scanning functionality
└── cargo_form_page.dart   # Cargo form management
```

## Getting Started

### Prerequisites

- Flutter SDK (latest version)
- Dart SDK
- Android Studio / Xcode (for mobile development)
- VS Code or preferred IDE

### Installation

1. Clone the repository:
```bash
git clone https://github.com/LOKITHRAJ/vahan-rakshak.git
```

2. Navigate to the mobile app directory:
```bash
cd vahan-rakshak/mobile-app
```

3. Install dependencies:
```bash
flutter pub get
```

4. Run the application:
```bash
flutter run
```

## Platform Support

- ✅ Android
- ✅ iOS
- ✅ Web
- ✅ Linux
- ✅ macOS
- ✅ Windows

## Development

This project follows Flutter's best practices and conventions. The application is structured for easy maintenance and scalability.

### Project Architecture

- `lib/` - Contains all the Dart source code
- `assets/` - Static resources like images
- `test/` - Unit and widget tests
- Platform-specific folders for native code integration

## Testing

Run tests using:
```bash
flutter test
```

## Building for Production

### Android
```bash
flutter build apk --release
```

### iOS
```bash
flutter build ios --release
```

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contact

- Project Owner: LOKITHRAJ
- Repository: [vahan-rakshak](https://github.com/LOKITHRAJ/vahan-rakshak)
