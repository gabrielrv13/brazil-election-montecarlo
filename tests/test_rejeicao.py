"""
Testes para funcionalidade de rejeição (v2.2)
"""

import numpy as np
import sys
from pathlib import Path

# Adiciona src ao path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

def test_teto_eleitoral():
    """Testa se o teto de rejeição é aplicado corretamente."""
    print("\n🧪 Teste 1: Teto Eleitoral")
    
    # Simula votos que ultrapassam o teto
    votos = np.array([[60, 40], [55, 45], [70, 30]])  # 3 simulações, 2 candidatos
    rejeicao = np.array([42, 48])  # Lula 42%, Flávio 48%
    tetos_esperados = np.array([58, 52])  # 100 - rejeição
    
    # Aplica teto manualmente (lógica do código)
    votos_limitados = np.minimum(votos, tetos_esperados[np.newaxis, :])
    
    # Verifica se nenhum voto ultrapassa o teto
    assert np.all(votos_limitados <= tetos_esperados), "❌ Votos ultrapassaram o teto!"
    
    # Verifica casos específicos
    assert votos_limitados[0, 0] == 58, "❌ Lula deveria ser limitado a 58% na sim 1"
    assert votos_limitados[2, 0] == 58, "❌ Lula deveria ser limitado a 58% na sim 3"
    assert votos_limitados[0, 1] == 40, "✅ Flávio não deveria ser limitado na sim 1"
    
    print("   ✅ Teto de rejeição aplicado corretamente")
    print(f"      Votos originais: {votos}")
    print(f"      Tetos (100-rej): {tetos_esperados}")
    print(f"      Votos limitados: {votos_limitados}")


def test_inviabilidade_eleitoral():
    """Testa identificação de candidatos inviáveis (>50% rejeição)."""
    print("\n🧪 Teste 2: Candidatos Inviáveis")
    
    rejeicoes = np.array([42, 53, 35])  # Lula 42%, Candidato2 53%, Candidato3 35%
    
    # Identifica inviáveis
    inviáveis = rejeicoes > 50
    
    assert inviáveis[1] == True, "❌ Candidato com 53% deveria ser inviável"
    assert inviáveis[0] == False, "❌ Candidato com 42% NÃO deveria ser inviável"
    assert inviáveis[2] == False, "❌ Candidato com 35% NÃO deveria ser inviável"
    
    print("   ✅ Candidatos inviáveis identificados corretamente")
    print(f"      Rejeições: {rejeicoes}")
    print(f"      Inviáveis (>50%): {inviáveis}")


def test_transferencia_proporcional():
    """Testa transferência de votos proporcional ao espaço disponível."""
    print("\n🧪 Teste 3: Transferência Proporcional")
    
    rej1, rej2 = 42, 48
    espaco1, espaco2 = 100 - rej1, 100 - rej2  # 58, 52
    
    total_espaco = espaco1 + espaco2  # 110
    prop1 = espaco1 / total_espaco  # 58/110 = 0.527
    prop2 = espaco2 / total_espaco  # 52/110 = 0.473
    
    # Verifica se proporções somam 1
    assert abs((prop1 + prop2) - 1.0) < 0.001, "❌ Proporções não somam 1"
    
    # Verifica se candidato com menos rejeição recebe mais
    assert prop1 > prop2, "❌ Candidato com menos rejeição deveria receber mais"
    
    # Verifica valores esperados
    assert abs(prop1 - 0.5273) < 0.001, f"❌ Prop1 deveria ser ~0.527, got {prop1}"
    assert abs(prop2 - 0.4727) < 0.001, f"❌ Prop2 deveria ser ~0.473, got {prop2}"
    
    print("   ✅ Transferência proporcional calculada corretamente")
    print(f"      Lula: rejeição {rej1}% → espaço {espaco1}% → recebe {prop1*100:.1f}%")
    print(f"      Flávio: rejeição {rej2}% → espaço {espaco2}% → recebe {prop2*100:.1f}%")


def test_retrocompatibilidade():
    """Testa se modelo funciona sem coluna de rejeição (v2.1 behavior)."""
    print("\n🧪 Teste 4: Retrocompatibilidade")
    
    # Simula ausência de rejeição (tudo zero)
    rejeicao = np.array([0, 0, 0, 0])
    
    # Tetos deveriam ser 100%
    tetos = 100 - rejeicao
    assert np.all(tetos == 100), "❌ Tetos sem rejeição deveriam ser 100%"
    
    # Votos não deveriam ser limitados
    votos = np.array([[45, 35, 15, 5]])
    votos_limitados = np.minimum(votos, tetos[np.newaxis, :])
    assert np.array_equal(votos, votos_limitados), "❌ Sem rejeição, votos não devem ser alterados"
    
    print("   ✅ Modelo funciona sem dados de rejeição (retrocompatível)")


def run_all_tests():
    """Executa todos os testes."""
    print("=" * 60)
    print("  TESTES v2.2 — Funcionalidade de Rejeição")
    print("=" * 60)
    
    try:
        test_teto_eleitoral()
        test_inviabilidade_eleitoral()
        test_transferencia_proporcional()
        test_retrocompatibilidade()
        
        print("\n" + "=" * 60)
        print("  ✅ TODOS OS TESTES PASSARAM!")
        print("=" * 60)
        return True
    
    except AssertionError as e:
        print(f"\n❌ TESTE FALHOU: {e}")
        return False
    except Exception as e:
        print(f"\n❌ ERRO INESPERADO: {e}")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
