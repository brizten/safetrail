# TrailSafe Mobile

Мобильный MVP TrailSafe на Expo/React Native. Работает на Android и iPhone из одной кодовой базы.

Проект закреплён на Expo SDK 54, чтобы открываться в Expo Go из App Store/Google Play.

## Запуск на телефоне

1. Установите Expo Go:
   - Android: Google Play;
   - iPhone: App Store.
2. Запустите проект:

```powershell
cd mobile
npm install
npm run start
```

3. Отсканируйте QR-код:
   - Android: камерой или Expo Go;
   - iPhone: камерой или Expo Go.

Если Expo Go пишет `Project is incompatible with this version of Expo Go`, очистите кэш Metro и запустите заново:

```powershell
cd mobile
npx expo start -c
```

После этого заново отсканируйте QR-код.

## Запуск на эмуляторе

Android:

```powershell
cd mobile
npm run android
```

iOS Simulator доступен только на macOS:

```bash
cd mobile
npm run ios
```

## Проверки

```powershell
cd mobile
npx tsc --noEmit
npx expo install --check
npx expo config --type public
```

## Сборка Android/iOS

Для production-сборок используйте EAS Build:

```powershell
cd mobile
npx eas-cli login
npx eas-cli build --platform android
npx eas-cli build --platform ios
```

Для iOS-сборки нужен Apple Developer account. Android-сборку можно получить как `.apk`/`.aab` в зависимости от профиля EAS.

## Безопасность

- Геолокация запрашивается только по кнопке в SOS-режиме.
- SOS-сообщение формируется локально.
- Звонок и SMS открываются только после подтверждения.
- Данные хранятся локально через AsyncStorage.

Это MVP, не замена спасательным службам, спутниковому маяку или профессиональной навигации.
