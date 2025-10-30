import PageMeta from "../../components/common/PageMeta";
import AuthLayout from "./AuthPageLayout";
import SignUpForm from "../../components/auth/SignUpForm";

export default function SignUp() {
  return (
    <>
      <PageMeta
        title="Huawei SignUp"
        description="This is Huawei SignUp page"
      />
      <AuthLayout>
        <SignUpForm />
      </AuthLayout>
    </>
  );
}
