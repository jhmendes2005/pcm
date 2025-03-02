from flask import Blueprint, request, jsonify, current_app, render_template, redirect, url_for
from flask_login import login_required, current_user
import stripe  # Importando Stripe
from datetime import datetime
from app.purchases.plans import PlanManager
from app.models import Purchase

# Configurar o blueprint
purchase = Blueprint('purchases', __name__)

# Configuração do Stripe
stripe.api_key = current_app.config['STRIPE_SECRET_KEY']

def criar_cliente(nome, email):
    # Criação de cliente no Stripe
    cliente = stripe.Customer.create(
        email=email,
        name=nome,
    )
    return cliente

@purchase.route('/planos')
def plans():
    # Obtém a lista de planos disponíveis
    plans = PlanManager.list_plans()
    # Filtra planos com ID diferente de 0
    plans = {int(plano_id): atributos for plano_id, atributos in plans.items() if int(plano_id) != 0}

    for plan in plans:
        print(plan)
    # Passa a chave de API para o template
    return render_template('purchases/plans.html', plans=plans)


@purchase.route('/pagamento', methods=['GET', 'POST'])
def pagamento():
    # Obtém a lista de planos disponíveis
    plans = PlanManager.list_plans()
    # Filtra planos com ID diferente de 0
    plans = {int(plano_id): atributos for plano_id, atributos in plans.items() if int(plano_id) != 0}

    # Obtém o plano selecionado da query string, se existir
    selected_plan_id = request.args.get('plan_id', type=int)

    # Passa a chave de API e o plano selecionado para o template
    return render_template('checkout.html', plans=plans, stripe_public_key=current_app.config['STRIPE_PUBLIC_KEY'], selected_plan_id=selected_plan_id)


@purchase.route('/processar-pagamento', methods=['POST'])
@login_required
def processar_pagamento():
    plano_id = request.form['plan_id']
    price = PlanManager.load_plan_from_json(plano_id)
    price = int(price['price'])
    periodo_meses = int(request.form.get('periodo_meses', 1))  # Por padrão, 1 mês
    email = current_user.email
    nome = current_user.name
    stripe_token = request.form['stripe_token']  # O token enviado do frontend

    # Verifica se o cliente já existe no Stripe
    clientes = stripe.Customer.list(email=email)
    if clientes.data:
        cliente_id = clientes.data[0].id
    else:
        cliente = criar_cliente(nome, email)
        cliente_id = cliente.id

    # Obtém detalhes do plano
    plano = PlanManager.get_user_plan(plano_id)
    # Verifica se o usuário já possui um plano ativo
    plano_ativo = Purchase.query.filter(
        Purchase.user_id == current_user.id,
        Purchase.data_expiracao > datetime.utcnow()
    ).first()

    if plano_ativo:
        return redirect(url_for('purchases.resultado_compra', resultado='Você já possui um plano ativo.'))
    
    try:
        # Criação do pagamento no Stripe com o payment_method_data
        payment_intent = stripe.PaymentIntent.create(
            amount=price,  # O valor em centavos
            currency='brl',  # Moeda
            customer=cliente_id,
            payment_method_data={
                'type': 'card',  # Tipo de método de pagamento
                'card': {
                    'token': stripe_token  # Token gerado no frontend
                }
            },
            automatic_payment_methods={  # Habilita a escolha automática do método de pagamento
                'enabled': True,
                'allow_redirects': 'never',  # Desabilita o redirecionamento
            },
            confirm=True,  # Confirmar o pagamento
            metadata={  # Dados extras
                'plano_id': plano_id,
                'periodo_meses': periodo_meses
            }
        )

        # Registrar a compra no banco de dados
        resultado_registro = PlanManager.register_purchase(current_user.id, plano_id, payment_intent.id, periodo_meses)
        
        # Redireciona para a tela de resultado com sucesso
        return redirect(url_for('purchases.resultado_compra', resultado='Compra registrada com sucesso!'))
    
    except stripe.error.CardError as e:
        # Redireciona para a tela de resultado com erro
        return redirect(url_for('purchases.resultado_compra', resultado=f"Erro no pagamento cartão erro: {e.user_message}"))
    except Exception as e:
        # Redireciona para a tela de resultado com erro genérico
        return redirect(url_for('purchases.resultado_compra', resultado=f"Erro no pagamento outro erro: {str(e)}"))


@purchase.route('/resultado-compra', methods=['GET'])
def resultado_compra():
    resultado = request.args.get('resultado', 'Erro ao processar compra.')
    return render_template('resultado_compra.html', resultado=resultado)


from datetime import datetime
from flask import render_template
from flask_login import login_required, current_user

@purchase.route('/faturas')
@login_required
def orders():
    # Obtém a assinatura do usuário e a data de expiração
    assinatura_atual, data_expiracao = PlanManager.get_user_plan(current_user.id)

    # Verifica se a assinatura_atual e data_expiracao não são None
    if assinatura_atual is None or data_expiracao is None:
        assinatura_atual = "Nenhuma assinatura encontrada"
        data_expiracao = None  # Ou uma data padrão, se necessário

    # Obtém todas as compras do usuário, ordenadas da mais recente para a mais antiga
    purchases = Purchase.query.filter_by(user_id=current_user.id).order_by(Purchase.id.desc()).all()
    
    # Exibe as compras no console (para debug)
    print(purchases)

    # Verifica se a assinatura está ativa ou vencida
    if data_expiracao and data_expiracao < datetime.now():
        status_plano = "Vencido"
    else:
        status_plano = "Ativo"

    # Verifica se o usuário tem compras
    if not purchases:
        mensagem = "Você ainda não tem compras registradas."
    else:
        mensagem = None

    # Renderiza a página com os dados
    return render_template(
        'purchases/orders.html', 
        status_plano=status_plano, 
        purchases=purchases, 
        assinatura_atual=assinatura_atual,
        mensagem=mensagem
    )


@purchase.route('/comprovante/<payment_intent_id>', methods=['GET'])
@login_required
def obter_comprovante(payment_intent_id):
    try:
        # Recupera o PaymentIntent usando o ID
        payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)

        # Verifica se o pagamento foi bem-sucedido
        if payment_intent.status == 'succeeded' and payment_intent.latest_charge:
            # Recupera os detalhes da cobrança
            charge = stripe.Charge.retrieve(payment_intent.latest_charge)
            
            # Obtém o URL do recibo
            receipt_url = charge.receipt_url
            if receipt_url:
                return redirect(receipt_url)
            else:
                return jsonify({"erro": "Comprovante não disponível."}), 404
        else:
            return jsonify({"erro": "Pagamento não realizado ou comprovante indisponível."}), 404

    except stripe.error.StripeError as e:
        return jsonify({"erro": f"Erro ao obter comprovante: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"erro": f"Erro inesperado: {str(e)}"}), 500
    

@purchase.route('/detalhes/<order_id>', methods=['GET'])
@login_required
def detalhes_pedido(order_id):
    try:
        # Verifica se o usuário é admin ou se ele é o dono do pedido
        if current_user.role != 'admin':
            purchase = Purchase.query.filter_by(id=order_id, user_id=current_user.id).first()
        else:
            purchase = Purchase.query.filter_by(id=order_id).first()

        if not purchase:
            return jsonify({"erro": "Compra não encontrada ou acesso não autorizado."}), 404

        # Log para verificar se a compra foi encontrada corretamente
        print(f"Compra encontrada: {purchase}")

        # Recupera o PaymentIntent na Stripe usando o payment_intent_id da compra
        payment_intent = stripe.PaymentIntent.retrieve(purchase.charge_id)

        # Verifica se o pagamento foi bem-sucedido
        if payment_intent.status == 'succeeded' and payment_intent.latest_charge:
            charge = stripe.Charge.retrieve(payment_intent.latest_charge)
            receipt_url = charge.receipt_url
        else:
            receipt_url = None

        # Log para verificar os dados do PaymentIntent
        print(f"PaymentIntent: {payment_intent}")
        print(f"Receipt URL: {receipt_url}")

        return render_template(
            "purchases/services/details.html",
            purchase=purchase,
            payment_intent=payment_intent,
            receipt_url=receipt_url
        )

    except stripe.error.StripeError as e:
        return jsonify({"erro": f"Erro ao recuperar informações: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"erro": f"Erro inesperado: {str(e)}"}), 500
