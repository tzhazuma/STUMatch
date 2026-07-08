import { NativeStackScreenProps, NativeStackNavigationProp } from '@react-navigation/native-stack';
import { BottomTabScreenProps } from '@react-navigation/bottom-tabs';
import { DiscoveryUserDetail, Section, User, Conversation } from '../types';

export type AuthStackParamList = {
  Login: undefined;
  Register: undefined;
};

export type MainTabParamList = {
  Discovery: undefined;
  Friends: undefined;
  Profile: undefined;
};

export type RootStackParamList = {
  Auth: undefined;
  MainTabs: undefined;
  UserDetail: { section: Section; userId: string };
  Chat: { conversationId: string; participant: User };
  Questionnaire: undefined;
};

export type AuthScreenProps<T extends keyof AuthStackParamList> =
  NativeStackScreenProps<AuthStackParamList, T>;

export type MainTabScreenProps<T extends keyof MainTabParamList> =
  BottomTabScreenProps<MainTabParamList, T>;

export type RootScreenProps<T extends keyof RootStackParamList> =
  NativeStackScreenProps<RootStackParamList, T>;

export type RootNavigationProp = NativeStackNavigationProp<RootStackParamList>;
