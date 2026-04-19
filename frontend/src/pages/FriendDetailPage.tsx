import { useParams } from "react-router-dom";

function FriendDetailPage() {
  const { friendId } = useParams();
  return (
    <section>
      <h1 className="text-2xl font-semibold">Detalhe do amigo</h1>
      <p className="mt-2 text-sm text-slate-600">
        ID: {friendId}. Conteudo sera implementado em 13.17.
      </p>
    </section>
  );
}

export default FriendDetailPage;
